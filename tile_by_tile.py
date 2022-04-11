# -*- coding: utf-8 -*-
"""
Created on Mon Mar  7 15:32:41 2022

@author: awatson
"""

from tifffile import imread, imwrite, TiffFile, TiffWriter
import zarr
import numpy as np
from itertools import product
from utils import bigTiffRequired
import numpy as np


# outFile = r'z:\testOut.tif'
# # RGB
# inFile = r'Z:\olympus slide scanner\alan_test\basicTest\lab_1\_Image_01_Overview_\stack1\frame_t.tif'

# # Multichannel
# inFile = r'Z:\olympus slide scanner\alan_test\basicTest\lab_1\_Image_06_\stack1\frame_t_0.tif'

# # Stack
# inFile = r'Z:\olympus slide scanner\alan_test\forLater\z stack test\_Image_02_\stack1\frame_t_0.tif'

# # Stack overview
# inFile = r'Z:\olympus slide scanner\alan_test\forLater\z stack test\_Image_Overview_01_\stack10000\frame_t_0.tif'

# # FAILING:
# inFile = r'H:\CBI\Mike\Slide Scanner\Freyberg\1ss6 brain slices fluo\_Image_05c\stack1\frame_t_0.tif'



# Clean tifffile zarr chunks

def tiles(data, tileshape):
    '''
    Given a tiff read as zarr store + the desired tileshape (tuple,len_2)
    This will yield a single numpy tile from the dataset
    '''
    
    loops = []
    for idx,_ in enumerate(tileshape):
        loops.append(
            range(0,data.shape[idx],tileshape[idx])
            )
     
    for num, items in enumerate(product(*loops)):
        
        slices = []
        for idx,ii in enumerate(items):
            slices.append(
                slice(ii,ii+tileshape[idx])
                )
        try:
            print('{} of {} chunks'.format(num,data.nchunks)) # Only works with zarr array with nchunks property
        except Exception:
            print('{} chunk'.format(num))
        yield np.squeeze(data[(...,*slices)])



def tiles_maxIP(data, tileshape, axes):
    '''
    Assume input in a z-stack.  Read 
    '''
    
    zindex = axes.index('Z')
    # zLayers = data.shape[zindex]
    loopAxes = [x for idx,x in enumerate(data.shape) if idx != zindex]
    loopTiles = [x for idx,x in enumerate(tileshape) if idx != zindex]
    
    loops = []
    for idx,_ in enumerate(loopTiles):
        loops.append(
            range(0,loopAxes[idx],loopTiles[idx])
            )
     
    for num, items in enumerate(product(*loops)):
        
        slices = []
        for idx,ii in enumerate(items):
            if idx == zindex:
                slices.append(slice(None))
            slices.append(
                slice(ii,ii+loopTiles[idx])
                )
        try:
            print('{} of {} chunks'.format(num,data.nchunks//data.shape[zindex])) # Only works with zarr array with nchunks property
            # print('{} of {} chunks'.format(num,data.nchunks))
        except Exception:
            print('{} chunk'.format(num))
        
        out = data[(...,*slices)]
        out = np.max(out,axis=zindex) # maxIP accross z-axis
        yield np.squeeze(out)




def copy_tile_by_tile_any_senario(inFile: str, outFile: str, axes: str, fallback_tileshape=(512,512), compression='zlib'):
    
    '''
    inFile: Str to a tiff file path
    outFile: Str to a output tiff file path - expects the extension to be ome.tif
    axes: Str to indicate axes order, expects (CZYX,ZYX,CYX,YX,YXS(ie. RGB))
    '''

    # Generator to yield tiles from a numpy-like object
    # Used to read individual tiles from input file
    
    axes = axes.upper()
    if axes == 'RGB':
        axes = 'YXS'
    XY_index = axes.index('YX')
    
    with imread(inFile, aszarr=True) as store:
        tif = zarr.open(store, mode='r')
        try:
            tileshape = tif.chunks
        except Exception:
            tileshape = fallback_tileshape
        
        
        imwrite(
            outFile,
            tiles(tif, tileshape),
            metadata={'axes': axes},
            bigtiff=bigTiffRequired(tif),
            tile=tileshape[XY_index:XY_index+2] if (tileshape[XY_index]%16==0 and tileshape[XY_index+1]%16==0) else fallback_tileshape,
            shape=tif.shape,
            dtype=tif.dtype,
            compression=compression
            )
    
    ## TODO:  Integrate copying (or creation of) multi-resolution series



def copy_tile_by_tile_multires(inFile: str, outFile: str, axes: str, fallback_tileshape=(512,512), compression='zlib', maxip=False):
    
    
    axes = axes.upper()
    if axes == 'RGB':
        axes = 'YXS'
    XY_index = axes.index('YX')

    with imread(inFile, aszarr=True) as store:
        tif = zarr.open(store, mode='r')
        try:
            tileshape = tif.chunks
        except Exception:
            tileshape = fallback_tileshape
        
    
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

    
def copy_tile_by_tile_multires_mip(inFile: str, outFile: str, axes: str, fallback_tileshape=(512,512), compression='zlib', maxip=False):
    
    
    axes = axes.upper()
    if axes == 'RGB':
        axes = 'YXS'
    XY_index = axes.index('YX')

    with imread(inFile, aszarr=True) as store:
        tif = zarr.open(store, mode='r')
        try:
            tileshape = tif.chunks
        except Exception:
            tileshape = fallback_tileshape
        
    
    with TiffFile(inFile) as tif_read:
        
        seriesNum = len(tif_read.series)
        
        with TiffWriter(outFile, bigtiff=tif_read.is_bigtiff) as tif_write:
            
            for series in range(seriesNum):
                
                with tif_read.series[series].aszarr() as img_store:
                    img = zarr.open(img_store)
                    
                    tileshape = img.chunks
                    
                    if series == 0:
                        tif_write.write(
                            tiles(img,tileshape) if maxip==False else tiles_maxIP(img,tileshape,axes),
                            subifds=seriesNum-1,
                            metadata={'axes': axes} if maxip==False else {'axes': axes.replace('Z','')},
                            tile=tileshape[XY_index:XY_index+2] if (tileshape[XY_index]%16==0 and tileshape[XY_index+1]%16==0) else fallback_tileshape,
                            shape=img.shape if maxip==False else tuple([x for idx,x in enumerate(img.shape) if idx != axes.index('Z')]),
                            dtype=img.dtype,
                            compression=compression
                            )
                    else:
                        tif_write.write(
                            tiles(img,tileshape) if maxip==False else tiles_maxIP(img,tileshape,axes),
                            # subfiletype=1,
                            metadata={'axes': axes} if maxip==False else {'axes': axes.replace('Z','')},
                            tile=tileshape[XY_index:XY_index+2] if (tileshape[XY_index]%16==0 and tileshape[XY_index+1]%16==0) else fallback_tileshape,
                            shape=img.shape if maxip==False else tuple([x for idx,x in enumerate(img.shape) if idx != axes.index('Z')]),
                            dtype=img.dtype,
                            compression=compression
                            )

# ###  Write OME RGB tile-by-tile
# data = np.random.randint(0, 2**12, (5000, 5000, 3), 'uint16')

# def tiles(data, tileshape):
#     for y in range(0, data.shape[0], tileshape[0]):
#         for x in range(0, data.shape[1], tileshape[1]):
#             yield data[y : y + tileshape[0], x : x + tileshape[1]]


# tifffile.imwrite(r'z:/temp.ome.tif', tiles(data, (16, 16)), tile=(16, 16),
#         shape=data.shape, dtype=data.dtype, photometric='rgb')


# def tile_sliceRGB(data, tileshape):
#     for y in range(0, data.shape[0], tileshape[0]):
#         for x in range(0, data.shape[1], tileshape[1]):
#             yield slice(y,y + tileshape[0]), slice(x,x + tileshape[1])



# with imread(r'z:/temp.ome.tif', aszarr=True) as store:
#     tif = zarr.open(store, mode='r')
#     image = np.asarray(tif)
    
#     tifffile.imwrite(r'z:/temp_copy.ome.tif', tiles(data, (512, 512)), tile=(512, 512),
#             shape=data.shape, dtype=data.dtype, photometric='rgb')
    
    

# # Clean tifffile zarr chunks
# def copy_tile_by_tile_RGB(inFile,outFile,tileshape=(512,512)):
    
#     # Generator to yield tiles from a numpy-like object
#     # Used to read individual tiles from input file
#     def tiles(data, tileshape):
#         for y in range(0, data.shape[0], tileshape[0]):
#             for x in range(0, data.shape[1], tileshape[1]):
#                 yield data[y : y + tileshape[0], x : x + tileshape[1]]

      
#     with imread(inFile, aszarr=True) as store:
#         tif = zarr.open(store, mode='r')
#         try:
#             tileshape = tif.chunks[0:2]
#         except Exception:
#             pass
    
#         imwrite(outFile, tiles(tif, tileshape), tile=tileshape,
#                 shape=data.shape, dtype=data.dtype, photometric='rgb')
        

    
# # Clean tifffile zarr chunks
# def copy_tile_by_tile_multichannel(inFile,outFile,tileshape=(1,512,512)):
    
#     # Generator to yield tiles from a numpy-like object
#     # Used to read individual tiles from input file
#     def tiles(data, tileshape):
         
#         for c in range(0, data.shape[0], tileshape[0]):
#             for y in range(0, data.shape[1], tileshape[1]):
#                 for x in range(0, data.shape[2], tileshape[2]):
#                     yield np.squeeze(data[c : c + tileshape[0], y : y + tileshape[1], x : x + tileshape[2]])

      
#     with imread(inFile, aszarr=True) as store:
#         tif = zarr.open(store, mode='r')
#         try:
#             tileshape = tif.chunks
#         except Exception:
#             pass
        
#         imwrite(outFile,tiles(tif, tileshape),metadata={'axes': 'CYX'},bigtiff=True,tile=tileshape[-2:],shape=tif.shape, dtype=tif.dtype)
        








# # Clean tifffile zarr chunks
# def copy_tile_by_tile_stack(inFile,outFile,tileshape=(1,1,512,512)):
    
#     # Generator to yield tiles from a numpy-like object
#     # Used to read individual tiles from input file
#     def tiles(data, tileshape):
#         n = 0
#         for c in range(0, data.shape[0], tileshape[0]):
#             for z in range(0, data.shape[1], tileshape[1]):
#                 for y in range(0, data.shape[2], tileshape[2]):
#                     for x in range(0, data.shape[3], tileshape[3]):
#                         n+=1
#                         print('{} of {} chunks'.format(n,tif.nchunks))
#                         yield np.squeeze(data[c : c + tileshape[0], z : z + tileshape[1], y : y + tileshape[2], x : x + tileshape[3]])

      
#     with imread(inFile, aszarr=True) as store:
#         tif = zarr.open(store, mode='r')
#         try:
#             tileshape = tif.chunks
#         except Exception:
#             pass
        
#         imwrite(outFile,tiles(tif, tileshape),metadata={'axes': 'CZYX'},bigtiff=True,tile=tileshape[-2:],shape=tif.shape, dtype=tif.dtype)













