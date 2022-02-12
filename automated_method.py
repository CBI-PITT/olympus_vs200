# -*- coding: utf-8 -*-
"""
Created on Wed Apr 14 10:32:03 2021

@author: awatson
"""

import glob, tifffile, os, imagecodecs
# from skimage import io, img_as_ubyte, img_as_uint
# from skimage.transform import rescale
import numpy as np
# from dask import delayed
# import dask
from tifffile import TiffFile, imread
from matplotlib import pyplot as plt
# import xml.dom.minidom
import zarr


# Name of output directory which will be at the same level as .vsi files
outputFolder = 'conversion_out'

# A list of location to be checked for acquired
rootDirs = [
    # r'Z:\olympus slide scanner\Conversion Test'
        # ,r'Z:\olympus slide scanner\Conversion Test\fluorecent'
        r'Z:\olympus slide scanner\alan_test'
    ]



def addCBIPath():
    import sys
    import os
    if os.name == 'nt':
        path = r"//136.142.29.170/CBI_FastStore/cbiPythonTools"
    else:
        path = r"/CBI_FastStore/cbiPythonTools"
    path = path.replace("\\","/")
    if any([x == path for x in sys.path]) == False:
        sys.path.append(path)
    
    ## Use these lines to import packages
    # from cbiPythonTools import tiffUtils as tu
    # from cbiPythonTools import file as fi
    # from cbiPythonTools import ims

##################################################################################

addCBIPath()
from cbiPythonTools import file as fi


rootDirs = [fi.formatPath(x) for x in rootDirs]

filesToProcessIN = []
filesToProcessOUT = []

def bigTiffRequired(image):
    """
    TiffClass with .image array
    Returns True if the size and data type of the array and bit type form >= 2GB and 
    requires a BifTiff format
    
    Else returns False
    """
    bifTiffCutoff = (2**32 - 2**25)/1024/1024/1024/2  ##Converted to GB (/1024/1024/1024) '/2' required to bring below 2GB or tiff fails to write
    # fileSize = tiffClass.image.shape[0]*tiffClass.image.shape[1]
    
    for num, ii in enumerate(image.shape):
        if num==0:
            fileSize = ii
        else:
            fileSize *= ii
        
    if str(image.dtype) == 'uint16':
        fileSize = fileSize*16-1
    if str(image.dtype) == 'uint8' or str(image.dtype) == 'ubyte':
        fileSize = fileSize*8-1
    fileSize = fileSize/8/1024/1024/1024
    if fileSize < bifTiffCutoff:
        return False
    else:
        return True


def vsiNameGenerator(imageSet, vsiFilePath, output='image'):
    '''
    output = 'image', 'overview', 'complete'
    '''
    
    if output == 'image':
        baseFormat = 'Image{}.vsi'
    
    if output == 'overview':
        baseFormat = 'Image{}_Overview.vsi'
    
    if output == 'complete':
        baseFormat = 'conv_complete_Image{}.txt'
    
    fName = baseFormat.format(
        '' if imageSet==0 
        else '_{}'.format(
            str(imageSet).zfill(2)
            )
        )
    
    return os.path.join(os.path.split(vsiFilePath)[0],fName)
        

def imageDirNameGenerator(vsiFilePath):
    '''
    Input: vsi file
    Output: directory associated with the vsi file
    '''
    
    noExt = os.path.splitext(vsiFilePath)[0]
    pathBase,fileBase = os.path.split(noExt)
    
    fName = '_{}_'.format(fileBase)
    return os.path.join(pathBase,fName)

def collectImageInfo(inFilePath):
    
    with TiffFile(inFilePath) as tif:
        
        tiffData = {}
        tiffData['ome_metadata'] = tif.ome_metadata # This is XML format and can be directly written to disk
        tiffData['resolutions'] = len(tif.series)
        tiffData['shape'] = tif.series[0].shape
        tiffData['dtype'] = tif.series[0].dtype
        tiffData['axes'] = tif.series[0].axes
        tiffData['ndim'] = tif.series[0].ndim
        
    return tiffData

def writeImage(imageArray,outFile,metaDict):
    
    compression='zlib'
    tile=(1024, 1024)
    
    try:
        print('Writing image: ' + outFile)
        
        # RGB (ie brightfield image)
        if metaDict['axes'] == 'YXS' and metaDict['shape'][-1] == 3:
            tifffile.imwrite(outFile,imageArray,bigtiff=bigTiffRequired(imageArray),photometric='rgb',compression=compression,tile=tile)
        
        elif metaDict['axes'] == 'YX' and metaDict['ndim'] == 2:
            tifffile.imwrite(outFile,imageArray,bigtiff=bigTiffRequired(imageArray),metadata={'axes': 'YX'},compression=compression,tile=tile)
            
        elif metaDict['axes'] == 'CYX' and metaDict['ndim'] == 3:
            tifffile.imwrite(outFile,imageArray,bigtiff=bigTiffRequired(imageArray),metadata={'axes': 'CYX'},compression=compression,tile=tile)
        
        elif metaDict['axes'] == 'CZYX' and metaDict['ndim'] == 4:
            tifffile.imwrite(outFile,imageArray,bigtiff=bigTiffRequired(imageArray),metadata={'axes': 'CZYX'},compression=compression,tile=tile)
        
    except Exception:
        print('An Image write failed')
        raise
    
    return


def convert(inFile,outFile):
    
    print('Collectng image information')
    metaDict = collectImageInfo(inFile)
    
    print('Reading image: ' + inFile)
    # with TiffFile(inFile) as tif:
    #     image = tif.series[0].asarray()
    
    # Faster read using zarr
    with imread(inFile, aszarr=True) as store:
        tif = zarr.open(store, mode='r')
        image = np.asarray(tif)
        
    
    writeImage(image,outFile,metaDict)

    path,file = os.path.split(outFile)
    os.makedirs(os.path.join(path,'meta'),exist_ok=True)
    outMeta = os.path.join(path,'meta',file + '.xml')
    with open(outMeta,'w') as meta:
        meta.write(metaDict['ome_metadata'])
    
    if metaDict['axes'] == 'CZYX' and metaDict['ndim'] == 4:
        ## Axis 1 is color, so maxIP is over axis 1
        # imageMax = np.max(image,axis=1,keepdims=True)
        image = np.max(image,axis=1)
        metaDict['axes'] == 'CYX'
        metaDict['ndim'] == 3
        if fileName[-8:] == '.ome.tif':
            outFile = fileName[:-8] + '_maxip.ome.tif'
        else:
            prefix, _ = os.path.splitext(outFile)
            outFile = prefix + '_maxip.ome.tif'
            
        writeImage(image,outFile,metaDict)
    
    return


for root in rootDirs:
    
    # Find vsi files
    vsiFiles = sorted(glob.glob(os.path.join(root,'**','*.vsi')))
    
    dataDirs = [os.path.split(x)[0] for x in vsiFiles]
    dataDirs = sorted(list(set(dataDirs)))
    
    for acquireDir in dataDirs:
        vsiFilesAcquireDir = sorted(glob.glob(os.path.join(acquireDir,'*.vsi')))
    
        # Assume the completed imaging sessions will be in pairs
        numDatasets = len(vsiFilesAcquireDir)//2
        
        # Generate names of vsi Image and Overview files
        # Generate name of conv_complete file
        for imageSet in range(numDatasets):
            
            imageName = vsiNameGenerator(imageSet, vsiFilesAcquireDir[0], output='image')
            print(imageSet)
            print(imageName)
            
            imageOverviewName = vsiNameGenerator(imageSet, vsiFilesAcquireDir[0], output='overview')
            print(imageOverviewName)
            
            imageComplete = vsiNameGenerator(imageSet, vsiFilesAcquireDir[0], output='complete')
            print(imageComplete)
            
            # Abort build if there is not an image complete file present
            if os.path.exists(imageComplete):
                continue
            
            # Abort build if there is not both an overview and image .vsi file
            # The presence of these files indicates that acquisition is complete
            if not os.path.exists(imageOverviewName) or \
                    not os.path.exists(imageName):
                        continue
            
            
            ## Create output DIR if it does not exist
            path, fileName = os.path.split(imageName)
            dirName = os.path.splitext(fileName)[0]
            outDir = os.path.join(path,outputFolder,dirName)
            os.makedirs(outDir,exist_ok=True)
            
            ## Do Overview data first
            imageDirs = sorted(glob.glob(os.path.join(imageDirNameGenerator(imageOverviewName),'*')))
            for ii in imageDirs:
                if os.path.split(ii)[1] == 'stack1':
                    inFile = glob.glob(os.path.join(ii,'*.tif'))[0]
                    outFile = os.path.join(outDir,'{}_label.ome.tif'.format(dirName))
                    convert(inFile,outFile)
                
                elif os.path.split(ii)[1] == 'stack10000':
                    inFile = glob.glob(os.path.join(ii,'*.tif'))[0]
                    outFile = os.path.join(outDir,'{}_overview.ome.tif'.format(dirName))
                    convert(inFile,outFile)
                    
            ## Do Image data next
            ## Currently assumes that there is ONLY 1 file int he Image directory
            ## This file is is the only file exported
            imageDirs = sorted(glob.glob(os.path.join(imageDirNameGenerator(imageName),'*')))
            for ii in imageDirs:
                
                inFile = sorted(glob.glob(os.path.join(ii,'*.tif')))[0]
                outFile = os.path.join(outDir,'{}.ome.tif'.format(dirName))
                convert(inFile,outFile)
                
                # elif os.path.split(ii)[1] == 'stack10000':
                #     inFile = glob.glob(os.path.join(ii,'*.tif'))[0]
                #     outFile = os.path.join(outDir,'{}_overview.ome.tif'.format(dirName))
                #     convert(inFile,outFile)    
                    
                # if 'stack1' in ii and not 'stack10' in ii
            ## Indicate that imageSet is complete by writing out file
            txt = '''
            This file is here to indicate that the cooresponding image directory
            has been converted.  Do not delete this file or the conversion will
            run again!
            '''
            with open(imageComplete,'w') as f:
                f.write(txt)
        
        
        



# def convertMultiRes(inFile,outFile):
    
#     print('Reading image: ' + inFile)
#     image = tifffile.imread(inFile)
#     # fi.mkdir(os.path.split(outFile)[0])
    
#     print('Writing image: ' + outFile)
    
#     minShape = 64
#     downSample = 0
    
    
#     with TiffWriter(outFile, bigtiff=bigTiffRequired(image)) as tif:
#         if len(image.shape) == 2:
#             fi.mkdir(os.path.split(outFile)[0])
            
#             currentShape = list(image.shape)
#             while all([x > minShape for x in currentShape]):
#                 currentShape = [x//2 for x in currentShape]
#                 downSample += 1
            
            
#             options = dict(tile=(256, 256), photometric='minisblack',metadata={'axes': 'YX'})
#             if downSample == 0:
#                 tif.write(image,**options)
#             else:
#                 tif.write(image,subifds=downSample,**options)
#                 for ii in range(downSample):
#                     print('Resizing Image')
#                     image = rescale(image,0.5)
#                     image = img_as_uint(image)
#                     tif.write(image,subfiletype=1,**options)
                    
        


