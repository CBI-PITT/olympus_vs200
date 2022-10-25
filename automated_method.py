# -*- coding: utf-8 -*-
"""
Created on Wed Apr 14 10:32:03 2021

@author: awatson
"""

import glob, os
import re
import time
# from skimage import io, img_as_ubyte, img_as_uint
# from skimage.transform import rescale
from dask import delayed
import dask
from distributed import Client
# from matplotlib import pyplot as plt
# import xml.dom.minidom
from utils import collectImageInfo
from tile_by_tile import copy_tile_by_tile_any_senario, copy_tile_by_tile_multires, copy_tile_by_tile_multires_mip
import tifffile


# Name of output directory which will be at the same level as .vsi files
outputFolder = 'conversion_out'

#redo == True will ignore the 'complete file' and rerun ALL conversions.
#Generally this should ALWAYS be False - specific conversions can be rerun 
#by simplyy deleting the specific conv_comkplete*.txt' file
redo = False

# A list of location to be checked for acquired
rootDirs = [
    # r'Z:\olympus slide scanner\Conversion Test'
        # ,r'Z:\olympus slide scanner\Conversion Test\fluorecent'
        # r'Z:\olympus slide scanner\alan_test\basicTest'
        # r'C:\code\testData\vs200'
        # r'Z:\olympus slide scanner\alan_test\forLater'
        r'h:\CBI\Mike\Slide Scanner',
        r'h:\CBI\Greg\Olympus Slide Scanner'
        # r'H:\CBI\Mike\Slide Scanner\Freyberg'
        # r'H:\CBI\Mike\Slide Scanner\Freyberg\1ss6 brain slices fluo'
        # r'H:\CBI\Mike\Slide Scanner\Freyberg\1ss6 brain slices fluo\_Image_05c\stack1'
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

    numbers_in_file_name = re.findall(r"\d\d", file)
    tray_number = numbers_in_file_name[0]
    slide_number = numbers_in_file_name[1]

    outDir = os.path.join(path, outputFolder, f"{file.split('_')[0]}_{tray_number}_{slide_number}")
    
    return outDir

def convert(inFile,outFile):
    
    print('Collectng image information')
    try:
        metaDict = collectImageInfo(inFile)
    except tifffile.tifffile.TiffFileError as e:  # errors on temp files
        print("WARNING:", e, inFile)
        return

    print('Reading image: ' + inFile)
    # with TiffFile(inFile) as tif:
    #     image = tif.series[0].asarray()
    
    ## https://gregoryszorc.com/blog/2017/03/07/better-compression-with-zstandard/
    compression=('zlib',6)
    # compression=('zstd',1)
    # compression=('lzma',2)
    # compression=None
    # copy_tile_by_tile_any_senario(inFile, outFile, axes=metaDict['axes'], fallback_tileshape=(512,512), compression=compression) #Only base resolution
    # copy_tile_by_tile_multires(inFile, outFile, axes=metaDict['axes'], fallback_tileshape=(512,512), compression=compression, maxip=False) #All subresolutions are copied
    copy_tile_by_tile_multires_mip(inFile, outFile, axes=metaDict['axes'], fallback_tileshape=(512,512), compression=compression, maxip=False)
    
    path,file = os.path.split(outFile)
    os.makedirs(os.path.join(path,'meta'),exist_ok=True)
    outMeta = os.path.join(path,'meta',file + '.xml')
    with open(outMeta,'w') as meta:
        meta.write(metaDict['ome_metadata'])
    
    if 'Z' in metaDict['axes'].upper():
        
        if outFile[-8:] == '.ome.tif':
            outFile = outFile[:-8] + '_maxip.ome.tif'
        else:
            prefix, _ = os.path.splitext(outFile)
            outFile = prefix + '_maxip.ome.tif'
            
        copy_tile_by_tile_multires_mip(inFile, outFile, axes=metaDict['axes'], fallback_tileshape=(512,512), compression=compression, maxip=True)
    
    return

def convert_delayed(inFile,outFile,imageComplete,txt):
    os.makedirs(os.path.split(outFile)[0],exist_ok=True)
    convert(inFile,outFile)
    with open(imageComplete,'w') as f:
        f.write(txt)
    return True
    

def automated_method():
    # ## Indicate that imageSet is complete by writing out file
    txt = '''
    This file indicates that the cooresponding image directory
    has been converted.  Do not delete this file or the conversion will
    run again!
    '''


    exceptions = []
    toProcess = []
    for root in rootDirs:
        # continue

        try:
            # Find vsi files
            vsiFiles = sorted(glob.glob(os.path.join(root,'**','*.vsi'),recursive=True))

            dataDirs = [os.path.split(x)[0] for x in vsiFiles]
            dataDirs = sorted(list(set(dataDirs)))

            for acquireDir in dataDirs:
                vsiFilesAcquireDir = sorted(glob.glob(os.path.join(acquireDir,'*.vsi')))

                # Generate names of vsi Image and Overview files
                # Generate name of conv_complete file
                # vsiFilePath = r'H:\CBI\Mike\Slide Scanner\Freyberg\1ss6 brain slices fluo\Image_01a.vsi'
                for vsiFilePath in vsiFilesAcquireDir:
                    inFile = None
                    try:
                        imageDir = imageDirNameGenerator(vsiFilePath)
                        print(vsiFilePath)
                        print(imageDir)

                        path,fileName,ext = pathParts(vsiFilePath)

                        imageComplete = vsiCompleteFile(vsiFilePath)
                        print(imageComplete)

                        # Abort build if there is an image complete file present
                        if os.path.exists(imageComplete) and redo == False:
                            continue


                        ## Create and retireve name of output DIR
                        outDir = outputDirGenerator(vsiFilePath,outputFolder)
                        if 'overview' in fileName.lower():
                            newName = fileName.replace('_Overview','')
                            p,f = os.path.split(outDir)
                            outDir = os.path.join(p,newName)


                        ## List folders in image directory
                        imageDirs = sorted(glob.glob(os.path.join(imageDir,'*')))
                        # Sometimes an underscore is not at the end of an image directory
                        # Remove the underscore and try again
                        if imageDirs == []:
                            imageDirs = sorted(glob.glob(os.path.join(imageDir[:-1],'*')))

                        ## Is it Overview data
                        if 'overview' in fileName.lower():
                            for ii in imageDirs:
                                if os.path.split(ii)[1] == 'stack1':
                                    try:
                                        inFile = glob.glob(os.path.join(ii,'*.tif'))[0]
                                    except IndexError as e:
                                        exceptions.append((ii, e))
                                        continue
                                    outFile = os.path.join(outDir,'{}_label.ome.tif'.format(newName))  # TODO newName can be undefined
                                    a = delayed(convert_delayed)(inFile,outFile,imageComplete,txt)
                                    toProcess.append(a)

                                elif os.path.split(ii)[1] == 'stack10000':
                                    try:
                                        inFile = glob.glob(os.path.join(ii,'*.tif'))[0]
                                    except IndexError as e:
                                        exceptions.append((ii, e))
                                        continue
                                    outFile = os.path.join(outDir,'{}_overview.ome.tif'.format(newName))
                                    a = delayed(convert_delayed)(inFile,outFile,imageComplete,txt)
                                    toProcess.append(a)

                                print('Queueing file {}: '.format(inFile))

                        else:
                            ## Do Image data next
                            ## Currently assumes that there is ONLY 1 file int he Image directory
                            ## This file is is the only file exported
                            for ii in imageDirs:
                                try:
                                    inFile = sorted(glob.glob(os.path.join(ii,'*.tif')))[0]
                                except IndexError as e:
                                    exceptions.append((ii, e))
                                    continue
                                _,f,_ = pathParts(ii)
                                filePostfix = str(int(f.split('stack')[-1]))
                                outFile = os.path.join(outDir,'{}_{}.ome.tif'.format(fileName,filePostfix))
                                a = delayed(convert_delayed)(inFile,outFile,imageComplete,txt)
                                toProcess.append(a)

                                print('Queueing file {}: '.format(inFile))

                        # ## Indicate that imageSet is complete by writing out file
                        # txt = '''
                        # This file indicates that the cooresponding image directory
                        # has been converted.  Do not delete this file or the conversion will
                        # run again!
                        # '''
                        # with open(imageComplete,'w') as f:
                        #     f.write(txt)


                    except Exception as e:
                        exceptions.append((inFile,e))
                        print(e)
                        continue


        except Exception as e:
            print(e)
            continue

    parallel = False
    dist = False
    if len(toProcess) > 0:
        print('Processing batch from: {}'.format(root))  # TODO root can be undefined
        if parallel == True:
            if dist == True:
                client = Client()
                toProcess = client.compute(toProcess)
                toProcess = client.gather(toProcess)
                client.close()
                del client
            else:
                toProcess = dask.compute(toProcess)
        else:
            for ii in toProcess:
                a = ii.compute()

    toProcess = []


if __name__ == "__main__":
    sleep_minutes = 10
    while True:
        automated_method()
        print(f"Waiting {sleep_minutes} minutes...")
        time.sleep(sleep_minutes * 60)
