# -*- coding: utf-8 -*-
"""
Created on Wed Apr 14 10:32:03 2021

@author: awatson
"""

import glob, os
# from skimage import io, img_as_ubyte, img_as_uint
# from skimage.transform import rescale
# from dask import delayed
# import dask
# from matplotlib import pyplot as plt
# import xml.dom.minidom
from utils import collectImageInfo
from tile_by_tile import copy_tile_by_tile_any_senario


# Name of output directory which will be at the same level as .vsi files
outputFolder = 'conversion_out'

# A list of location to be checked for acquired
rootDirs = [
    # r'Z:\olympus slide scanner\Conversion Test'
        # ,r'Z:\olympus slide scanner\Conversion Test\fluorecent'
        # r'Z:\olympus slide scanner\alan_test\basicTest'
        # r'C:\code\testData\vs200'
        r'Z:\olympus slide scanner\alan_test\forLater'
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



def pathParts(vsiFilePath):
    path,file = os.path.split(vsiFilePath)
    fileName,ext = os.path.splitext(file)
    return path,fileName,ext

def vsiCompleteFile(vsiFilePath):
    path,fileName,_ = pathParts(vsiFilePath)
    return os.path.join(path,'conv_complete_{}.txt'.format(fileName))

def imageDirNameGenerator(vsiFilePath):
    '''
    Input: vsi file
    Output: directory associated with the vsi file
    '''
    path,fileName,_ = pathParts(vsiFilePath)
    dir_name = '_{}_'.format(fileName)
    return os.path.join(path,dir_name)
  

def outputDirGenerator(vsiFilePath,outputFolder):
    '''
    Take .vsi file and outputFolder.
    
    Output: path to directory
    '''
    
    path,file,_ = pathParts(vsiFilePath)
    
    outDir = os.path.join(path,outputFolder,file)
    
    return outDir

def convert(inFile,outFile):
    
    print('Collectng image information')
    metaDict = collectImageInfo(inFile)
    
    print('Reading image: ' + inFile)
    # with TiffFile(inFile) as tif:
    #     image = tif.series[0].asarray()
    
    compression='zlib'
    compression=None
    copy_tile_by_tile_any_senario(inFile, outFile, axes=metaDict['axes'], fallback_tileshape=(512,512), compression=compression)
    
    path,file = os.path.split(outFile)
    os.makedirs(os.path.join(path,'meta'),exist_ok=True)
    outMeta = os.path.join(path,'meta',file + '.xml')
    with open(outMeta,'w') as meta:
        meta.write(metaDict['ome_metadata'])
    
    ## TODO: Make maxip work tile by tile
    # if metaDict['axes'] == 'CZYX' and metaDict['ndim'] == 4:
    #     ## Axis 1 is color, so maxIP is over axis 1
    #     # imageMax = np.max(image,axis=1,keepdims=True)
    #     image = np.max(image,axis=1)
    #     metaDict['axes'] == 'CYX'
    #     metaDict['ndim'] == 3
    #     if fileName[-8:] == '.ome.tif':
    #         outFile = fileName[:-8] + '_maxip.ome.tif'
    #     else:
    #         prefix, _ = os.path.splitext(outFile)
    #         outFile = prefix + '_maxip.ome.tif'
            
    #     writeImage(image,outFile,metaDict)
    
    return



for root in rootDirs:
    
    try:
        # Find vsi files
        vsiFiles = sorted(glob.glob(os.path.join(root,'**','*.vsi'),recursive=True))
        
        dataDirs = [os.path.split(x)[0] for x in vsiFiles]
        dataDirs = sorted(list(set(dataDirs)))
        
        for acquireDir in dataDirs:
            vsiFilesAcquireDir = sorted(glob.glob(os.path.join(acquireDir,'*.vsi')))
            
            # Generate names of vsi Image and Overview files
            # Generate name of conv_complete file
            for vsiFilePath in vsiFilesAcquireDir:
                
                try:
                    imageDir = imageDirNameGenerator(vsiFilePath)
                    print(vsiFilePath)
                    print(imageDir)
                    
                    path,fileName,ext = pathParts(vsiFilePath)
                    
                    imageComplete = vsiCompleteFile(vsiFilePath)
                    print(imageComplete)
                    
                    # Abort build if there is an image complete file present
                    if os.path.exists(imageComplete):
                        continue
                    
                    
                    ## Create and retireve name of output DIR
                    outDir = outputDirGenerator(vsiFilePath,outputFolder)
                    if 'overview' in fileName.lower():
                        newName = fileName.replace('_Overview','')
                        p,f = os.path.split(outDir)
                        outDir = os.path.join(p,newName)
                    os.makedirs(outDir,exist_ok=True)
                    
                    ## List folders in image directory
                    imageDirs = sorted(glob.glob(os.path.join(imageDir,'*')))
                    
                    ## Is it Overview data
                    if 'overview' in fileName.lower():
                        for ii in imageDirs:
                            if os.path.split(ii)[1] == 'stack1':
                                inFile = glob.glob(os.path.join(ii,'*.tif'))[0]
                                outFile = os.path.join(outDir,'{}_label.ome.tif'.format(newName))
                                convert(inFile,outFile)
                            
                            elif os.path.split(ii)[1] == 'stack10000':
                                inFile = glob.glob(os.path.join(ii,'*.tif'))[0]
                                outFile = os.path.join(outDir,'{}_overview.ome.tif'.format(newName))
                                convert(inFile,outFile)
                    
                    else:
                        ## Do Image data next
                        ## Currently assumes that there is ONLY 1 file int he Image directory
                        ## This file is is the only file exported
                        for ii in imageDirs:
                            
                            inFile = sorted(glob.glob(os.path.join(ii,'*.tif')))[0]
                            _,f,_ = pathParts(ii)
                            filePostfix = str(int(f.split('stack')[-1]))
                            outFile = os.path.join(outDir,'{}_{}.ome.tif'.format(fileName,filePostfix))
                            convert(inFile,outFile)
                            
                    ## Indicate that imageSet is complete by writing out file
                    txt = '''
                    This file indicates that the cooresponding image directory
                    has been converted.  Do not delete this file or the conversion will
                    run again!
                    '''
                    with open(imageComplete,'w') as f:
                        f.write(txt)
                
                except Exception:
                    continue

    except Exception:
        continue
        
        




