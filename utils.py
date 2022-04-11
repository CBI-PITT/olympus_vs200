# -*- coding: utf-8 -*-
"""
Created on Tue Mar  8 15:51:22 2022

@author: awatson
"""

from tifffile import TiffFile

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


def bigTiffRequired(image):
    """
    np-like array with nbytes parameter
    Returns True if the size and data type of the array and bit type form >= 4GB and 
    requires a BifTiff format
    
    Else returns False
    """
    bifTiffCutoff = 2**32 - 2**25  # 4GB
    # fileSize = tiffClass.image.shape[0]*tiffClass.image.shape[1]
    
    if image.nbytes < bifTiffCutoff:
        return False
    else:
        return True


# def bigTiffRequired(image):
#     """
#     TiffClass with .image array
#     Returns True if the size and data type of the array and bit type form >= 2GB and 
#     requires a BifTiff format
    
#     Else returns False
#     """
#     bifTiffCutoff = (2**32 - 2**25)/1024/1024/1024/2  ##Converted to GB (/1024/1024/1024) '/2' required to bring below 2GB or tiff fails to write
#     # fileSize = tiffClass.image.shape[0]*tiffClass.image.shape[1]
    
#     for num, ii in enumerate(image.shape):
#         if num==0:
#             fileSize = ii
#         else:
#             fileSize *= ii
        
#     if str(image.dtype) == 'uint16':
#         fileSize = fileSize*16-1
#     if str(image.dtype) == 'uint8' or str(image.dtype) == 'ubyte':
#         fileSize = fileSize*8-1
#     fileSize = fileSize/8/1024/1024/1024
#     if fileSize < bifTiffCutoff:
#         return False
#     else:
#         return True





