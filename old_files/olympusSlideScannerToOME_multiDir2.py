# -*- coding: utf-8 -*-
"""
Created on Wed Apr 14 10:32:03 2021

@author: awatson
"""

import glob, tifffile, os, imagecodecs
from skimage import io
from skimage.transform import rescale
import numpy as np
from dask import delayed
import dask



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
from cbiPythonTools import tiffUtils as tu
from cbiPythonTools import file as fi
from cbiPythonTools import ims

## pip install imagecodecs
## conda install -c anaconda imagecodecs

## Notes:
## Files from olympus slide scanner save stack file as 4 dimention arrays using 
## jpeg2000 compression
## DIMS:  (c,y,x,z)

# image.tags.keys()
# Out[31]: dict_keys(['image_width', 'image_length', 'bits_per_sample', 'compression', 'photometric', 'image_description', 'orientation', 'samples_per_pixel', 'planar_configuration', 'tile_width', 'tile_length', 'tile_offsets', 'tile_byte_counts', 'sample_format', '434']

###  DUMB  ###
## Olympus stores color only files as (c,y,x)
## Olympus stores z-stacks as (c,z,y,x)
###  DID I SAY DUMB? ###

## tifffile module can save OME-TIFF dims = (z,c,y,x), file extension= 'ome.tif'

## Thus 4 dim ome's read by tiffile must have axis 0,1 swapped to 1,0

## Save all files as max instensity projection ome.tif
OME = True
MaxP = False

# rootDirs = [
#         r"H:\Public\finn-o\VS200 Opal",
#         r'H:\Public\simslucas-s\dermody',
#         r'H:\Public\simslucas-s\Histo Core',
#         r'H:\Public\simslucas-s\Kemaladewi',
#         r'H:\Public\simslucas-s\krishna histo slides',
#         r'H:\Public\simslucas-s\Simslucas',
#         r"H:\Public\dutta-p\VS200\Brightfield 20x",
#         r"H:\Public\dutta-p\VS200\Human",
#         r"H:\Public\dutta-p\VS200\IF-VMDM",
#         r"H:\Public\dutta-p\VS200\Mason tri-chrome",
#         r"H:\Public\tzeng-e\Pulsatile Pump\eNOS 03-22-21",
#         r"H:\Public\tzeng-e\Pulsatile Pump\eNOS V",
#         r"H:\Public\tzeng-e\Trials\pig aorta",
#         r"H:\CBI\Patricia\vs200 Alvikas-Neal",
#         r"H:\CBI\Patricia\vs200 Ting-Billiar Oil red O",
#         r"H:\CBI\Patricia\Ting VS200",
#         r"H:\Public\Cheetham\VS200 Demo",
#         r"H:\Public\Cheetham\VS200 Demo\20016_GL",
#         r"H:\Public\Cheetham\VS200 Demo\190903_DA",
#         r"H:\Public\Cheetham\VS200 Demo\190913_GL",
#         r"H:\Public\Cheetham\VS200 Demo\191015_GL1",
#         r"H:\Public\Cheetham\VS200 Demo\191015_GL2",
#         r"H:\Public\Cheetham\VS200 Demo\191015-GL3",
#         r"H:\Public\Cheetham\VS200 Demo\191122 GL",
#         r"H:\Public\Cheetham\VS200 Demo\191202_GL1",
#         r"H:\Public\Cheetham\VS200 Demo\191202_GL2",
#         r"H:\Public\Cheetham\VS200 Demo\200128_VJ",
#         r"H:\Public\Cheetham\VS200 Demo\200219_VJ",
#         r"H:\Public\Cheetham\VS200 Demo\200226_VJ1",
#         r"H:\Public\Cheetham\VS200 Demo\200226_VJ2",
#         r"H:\Public\Cheetham\VS200 Demo\480934_6_2_CR",
#         r"H:\Public\Al Ghouleh\vs200"  
#         ]

# rootDirs = [
#         r"H:\Public\freyberg-z\For Alan\Jenesis_20x-round1",
#         r'H:\Public\freyberg-z\For Alan\Jenesis_20x-round2',
#         r'H:\Public\freyberg-z\For Alan\Stef_D1-D2-D3-NPAS2',
#         r"H:\Public\freyberg-z\VS200 demo\D1C1NPASC2D3C3"
#         ]

rootDirs = [
    r'Z:\olympus slide scanner\Conversion Test\Brightfield',
    r'Z:\olympus slide scanner\Conversion Test\fluorecent'
    ]



if MaxP==True:
    outDirs = [x + '_CONV_MaxP' for x in rootDirs]
else:
    outDirs = [x + '_CONV' for x in rootDirs]
rootDirs = [fi.formatPath(x) for x in rootDirs]
outDirs = [fi.formatPath(x) for x in outDirs]

filesToProcessIN = []
filesToProcessOUT = []
for root,out in zip(rootDirs,outDirs):
    # dirs = os.path.join(root,'_Image_*_','**','frame_t_[0-9].tif')
    dirs = os.path.join(root,'_Image_*','**','frame_t*.tif')
    filesIn = sorted(glob.glob(dirs))
    filesOut = [x.replace(root,out) for x in filesIn]
    
    ## Works Limux only to temp redirect all outputs to FastStore
    # filesOut = [x.replace('/CBI_Hive/','/CBI_FastStore/VS200/') for x in filesOut]
    
    if OME==True and MaxP==False:
        filesOut = [x[:-4] + '.ome.tif' for x in filesOut]
    if OME==True and MaxP==True:
        filesOut = [x[:-4] + '_MaxP.ome.tif' for x in filesOut]
        
    filesToProcessIN.extend(filesIn)
    filesToProcessOUT.extend(filesOut)


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

def convert(inFile,outFile):
    print('Reading image: ' + inFile)
    image = tifffile.imread(inFile)
    fi.mkdir(os.path.split(outFile)[0])
    
    ## Fix dimentions to align with appropriate OME-TIFF dims
    if len(image.shape) == 3:
        # image.image = np.moveaxis(image.image,[0,1,2],[1,2,0])
        pass
    elif len(image.shape) == 4:
        # image.image = np.moveaxis(image.image,[0,1,2,3],[1,2,3,0])
        # image.image = np.moveaxis(image.image,[0,1],[1,0])
        pass
    
    if MaxP == True and len(image.shape) == 4:
        ## Axis 1 is color, so maxIP is over axis 1
        image = np.max(image,axis=1,keepdims=True)
        # image.image = np.max(image.image,axis=1)
        # image.image = np.expand_dims(image.image,1)
        print(image.shape)
    
    
    
    print('Writing image: ' + outFile)
    
    try:
        # with tifffile.TiffWriter(outFile,bigtiff=bigTiffRequired(image),ome=OME) as tif:
        #     if len(image.shape) == 2:
        #         tif.write(data=image,bigtiff=bigTiffRequired(image),metadata={'axes': 'YX'})
        #     elif len(image.shape) == 3:
        #         tif.write(data=image,bigtiff=bigTiffRequired(image),metadata={'axes': 'YX'})
        #     elif len(image.shape) == 4:
        #         tif.write(data=image,bigtiff=bigTiffRequired(image),metadata={'axes': 'CZYX'})
    
        if len(image.shape) == 2:
            # tifffile.imwrite(outFile,image,bigtiff=bigTiffRequired(image),tile=(512,512),metadata={'axes': 'CYX'})
            tifffile.imwrite(outFile,image,bigtiff=bigTiffRequired(image),metadata={'axes': 'YX'})
        elif len(image.shape) == 3:
            ## Assume RGB of last dim == 3
            if image.shape[-1] == 3:
                # image = np.moveaxis(image,[-1],[0])
                tifffile.imwrite(outFile,image,bigtiff=bigTiffRequired(image),photometric='rgb')
            # tifffile.imwrite(outFile,image,bigtiff=bigTiffRequired(image),tile=(512,512),metadata={'axes': 'CYX'})
            else:
                tifffile.imwrite(outFile,image,bigtiff=bigTiffRequired(image),metadata={'axes': 'CYX'})
        elif len(image.shape) == 4:
            # tifffile.imwrite(outFile,image,bigtiff=bigTiffRequired(image),tile=(512,512),metadata={'axes': 'CZYX'})
            tifffile.imwrite(outFile,image,bigtiff=bigTiffRequired(image),metadata={'axes': 'CZYX'})
    except Exception:
        print('An Image write failed')
        raise
    return

toConvert = []
for inFile,outFile in zip(filesToProcessIN,filesToProcessOUT):
    
    print('Staging ' + inFile)
    a = delayed(convert)(inFile,outFile)
    # toConvert.append(a.compute())
    toConvert.append(a)
    # convert(inFile,outFile)
    
toConvert = dask.compute(toConvert)

# for ii in toConvert:
#     ii.compute()
        
        


# file = r"H:\CBI\Katherine\VS200 stuff ALAN PATRICIA LOOK HERE\this is a small 40x 4-color tiff created by the VS200.tif"
# file = r"H:\CBI\Katherine\VS200 stuff ALAN PATRICIA LOOK HERE\this is a small 40x 4-color tiff exported by cellsens.tif"
# file = r"d:\multi-channel-z-series.ome.tif"
# file = r"d:\multi-channel-4D-series.ome.tif"
# file = r"d:\multi-channel.ome.tif"
# file = r"d:\z-series.ome.tif"
# image = tu.tiff(file)
# image = image.image

# if len(image.shape) == 4:
#     image = np.swapaxes(image,0,3)

# maxProj = []
# for ii in image:
#     maxProj.append(np.max(ii,axis=0))

# maxProj = np.stack(maxProj)


# image = np.swapaxes(image,0,3)

# # tifffile.imsave('D:/testOut.tiff',maxProj)
# # imageio.mimwrite('D:/testOut.tiff',maxProj)

# with tifffile.TiffWriter('D:/testOutBTIFF.tiff',bigtiff=True) as tif:
#     for ii in maxProj:
#         tif.write(ii, photometric='minisblack')
        
# tifffile.imwrite('D:/testOutBTIFF.ome.tiff',np.moveaxis(image,[0,1,2,3],[1,2,3,0]))
# tifffile.imwrite('D:/testOutMAXProjBigTIFF.ome.tiff',maxProj, bigtiff=True)

