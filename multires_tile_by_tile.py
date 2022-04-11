# -*- coding: utf-8 -*-
"""
Created on Wed Mar  9 10:40:12 2022

@author: awatson
"""

'''
Atempt at copying all multi-scale image data
'''

from tifffile import imread, imwrite, TiffFile, TiffWriter
import zarr
import numpy as np
from itertools import product
from utils import bigTiffRequired
from tile_by_tile import tiles
from utils import collectImageInfo

# RGB
inFile = r'Z:\olympus slide scanner\alan_test\basicTest\lab_1\_Image_01_Overview_\stack1\frame_t.tif'
inFile = r'Z:\olympus slide scanner\alan_test\forLater\Bright, no z, multi image\_Image_\stack1\frame_t.tif'

# # Multichannel
# inFile = r'Z:\olympus slide scanner\alan_test\basicTest\lab_1\_Image_06_\stack1\frame_t_0.tif'
inFile = r'Z:\olympus slide scanner\alan_test\basicTest\lab_1\_Image_\stack1\frame_t_0.tif'

# # Stack
# inFile = r'Z:\olympus slide scanner\alan_test\forLater\z stack test\_Image_02_\stack1\frame_t_0.tif'

# # Stack overview
# inFile = r'Z:\olympus slide scanner\alan_test\forLater\z stack test\_Image_Overview_01_\stack10000\frame_t_0.tif'

outFile = '//136.142.29.170/CBI_FastStore/out_multires_test.ome.tif'
# outFile = '//136.142.29.170/CBI_FastStore/out_multires_test.tif'

fallback_tileshape = (512,512)
compression = None


metaDict = collectImageInfo(inFile)

axes = metaDict['axes'].upper()
if axes == 'RGB':
    axes = 'YXS'
XY_index = axes.index('YX')


with imread(inFile, aszarr=True) as store:
    tif = zarr.open(store, mode='r')
    try:
        tileshape = tif.chunks
    except Exception:
        tileshape = fallback_tileshape
    
    bigtiff = bigTiffRequired(tif)
    
    



# with TiffWriter(outFile) as tif_write:

with TiffFile(inFile) as tif_read:
    
    seriesNum = len(tif_read.series)
    
    with TiffWriter(outFile, bigtiff=tif_read.is_bigtiff) as tif_write:
        
        for series in range(seriesNum):
            
            with tif_read.series[series].aszarr() as img_store:
                img = zarr.open(img_store)
                
                tileshape = img.chunks
                
                if series == 0:
                    tif_write.write(
                        tiles(img,tileshape),
                        subifds=seriesNum-1,
                        metadata={'axes': axes},
                        tile=tileshape[XY_index:XY_index+2] if (tileshape[XY_index]%16==0 and tileshape[XY_index+1]%16==0) else fallback_tileshape,
                        shape=img.shape,
                        dtype=img.dtype,
                        compression=compression
                        )
                else:
                    tif_write.write(
                        tiles(img,tileshape),
                        # subfiletype=1,
                        metadata={'axes': axes},
                        tile=tileshape[XY_index:XY_index+2] if (tileshape[XY_index]%16==0 and tileshape[XY_index+1]%16==0) else fallback_tileshape,
                        shape=img.shape,
                        dtype=img.dtype,
                        compression=compression
                        )

    

        

