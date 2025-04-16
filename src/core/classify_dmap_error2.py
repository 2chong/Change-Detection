import geopandas as gpd
import matplotlib.pyplot as plt
from shapely.geometry import box
import numpy as np
import rasterio
import os
import pandas as pd
from rasterio.warp import calculate_default_transform, reproject, Resampling
import matplotlib as mpl
from matplotlib.ticker import ScalarFormatter
import utils


def classify_dmap_error_pipeline(prev_dmap, cur_dmap, seg, image, output_path):
    prev_dmap = utils.import_shapefile(prev_dmap, crs=5179)