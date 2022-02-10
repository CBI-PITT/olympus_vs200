# -*- coding: utf-8 -*-
"""
Created on Wed Apr 14 10:32:03 2021

@author: awatson
"""

import glob, tifffile, os
from skimage import io
import numpy as np



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
## Olympus stores color only files as (y,x,c)
## Olympus stores z-stacks as (c,y,x,z)
###  DID I SAY DUMB? ###


## tifffile require dims (z,y,x,c)

## tifffile can save OME-TIFF dims = (z,c,y,x), file extension= 'ome.tif'

## Save all files as max instensity projection ome.tif
OME = True
MaxP = True

rootDir = r"H:\Public\freyberg-z\VS200 demo\D1C1NPASC2D3C3"
rootDir = fi.formatPath(rootDir)
outDir = r"D:\Public\freyberg-z\VS200 demo\D1C1NPASC2D3C3_MAXP"
outDir = fi.formatPath(outDir)
dirs = os.path.join(rootDir, '_Image_*_','**','frame_t_[0-9].tif')
filesIn = glob.glob(dirs)
filesIn = [fi.formatPath(x) for x in filesIn]

filesOut = [x.replace(rootDir,outDir) for x in filesIn]
if OME==True and MaxP==False:
    filesOut = [x[:-4] + '.ome.tif' for x in filesOut]
if OME==True and MaxP==True:
    filesOut = [x[:-4] + '_MaxP.ome.tif' for x in filesOut]


for inFile,outFile in zip(filesIn,filesOut):
    
    print('Reading image: ' + inFile)
    image = tu.tiff(inFile)
    fi.mkdir(os.path.split(outFile)[0])
    
    ## Fix dimentions to align with ACTUAL OME-TIFF
    if len(image.image.shape) == 3:
        image.image = np.moveaxis(image.image,[0,1,2],[1,2,0])
        pass
    elif len(image.image.shape) == 4:
        image.image = np.moveaxis(image.image,[0,1,2,3],[1,2,3,0])
        pass
    
    if MaxP == True and len(image.image.shape) == 4:
        image.image = np.max(image.image,0)
    
    
    
    print('Writing image: ' + outFile)
    tifffile.imwrite(outFile,image.image)
        
        


# file = r"H:\CBI\Katherine\VS200 stuff ALAN PATRICIA LOOK HERE\this is a small 40x 4-color tiff created by the VS200.tif"
# file = r"H:\CBI\Katherine\VS200 stuff ALAN PATRICIA LOOK HERE\this is a small 40x 4-color tiff exported by cellsens.tif"
# file = r"d:\multi-channel-z-series.ome.tif"
# file = r"d:\multi-channel-4D-series.ome.tif"
# file = r"d:\multi-channel.ome.tif"
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

