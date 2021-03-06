# -*- coding: utf-8 -*-
"""
Created on Fri Sep 27 23:23:03 2019

@author: fenghuijian

Introduction: We use the Hierarchical Data Format V5(hdf5) file for data transmission between Python platform and R platform,
so as to achieve the purpose of reading data quickly and conveniently.Below, we will abbreviate hdf5 as h5.
"""


###  import the packages
from asyncio.events import get_running_loop
import scipy
import scanpy as sc
import pandas as pd
import numpy as np
from scipy import sparse
import anndata
from pandas.api.types import is_string_dtype, is_categorical_dtype, is_bool_dtype, is_float_dtype, is_integer_dtype, is_object_dtype
import h5py
from typing import Union
import re
import os

from scipy.sparse.sputils import matrix

### adata write the h5 file
def write_h5(adata: anndata.AnnData,
             file: Union[str, None] = None,
             assay_name: str = 'RNA',
             save_X:bool = True,
             save_graph:bool = True
             ) -> None:
    """
    The adata object is converted to H5 file that R can read

    Parameters:
    ----------
    adata : anndata.AnnData.
    file : The h5 file
    assy_name : Denotes which omics data to save. Default is 'RNA'. Available options are:
                'RNA': means that this omics data is scRNA-seq data
                'spatial': means that this omics data is spatial data generated by 10x Genomics Visium toolkits
    save_X : 
    save_graph : Default is False , determing whether to save the graph(cell-cell similarity network). scanpy graph is different from seruat graph. Their relationship are 
                 set {"distances": "knn", "connectivities": "snn"} roughly.
    ----------

    Usage:
    -----
    >>> import PyIOH5
    >>> PyIOH5.write_h5(adata = adata, file='filename.h5',save_raw=True,save_graph=True,save_spatial=Fasle)
    -----
    """
    # glabol function
    def namestr(obj, namespace):
        return [name for name in namespace if namespace[name] is obj]
    if file is None:
        raise OSError("No such file or directory")
    if not isinstance(adata, anndata.AnnData):
        raise TypeError("object '%s' class is not anndata.AnnData object" % namestr(adata, globals())[0])
    # w Create file, truncate if exists
    h5 = h5py.File(name=file, mode="w")
    try:
        adata_to_h5(adata=adata, h5=h5,assay_name=assay_name,save_X=save_X,save_graph=save_graph)
        h5.attrs['assay_name'] = np.array([assay_name], dtype=h5py.special_dtype(vlen=str))
    except Exception as e:
        print('Error:', e)
    finally:
        h5.close()
    return


### adata convert to the h5 file 
def adata_to_h5(adata: anndata.AnnData,
                h5: h5py.File,
                assay_name: Union[str, None] = 'RNA',
                save_graph:bool = False,
                save_X:bool = False
                ) -> None:
    """

    The adata object is converted to H5 file that R can read

    Parameters:
    ----------
    adata: anndata.AnnData
    h5: h5py.File
    assy_name : Denotes which omics data to save. Default is 'RNA'. Available options are:
                'RNA': means that this omics data is scRNA-seq data
                'spatial': means that this omics data is spatial data generated by 10x Genomics Visium toolkits
    save_raw : Default is True, determining whether to save adata.raw.X. adata.X and adata.raw.X will be changed in the scanpy pipeline. None: save adata.X & adata.raw.X 
               when adata.X.shape == adata.raw.X.shape. True: save adata.raw.X in any case. Fasle: save adata.X in any case.
    save_graph : Default is False , determing whether to save the graph(cell-cell similarity network). scanpy graph is different from seruat graph. Their relationship are 
                 set {"distances": "knn", "connectivities": "snn"} roughly.
    ----------

    Usage:
    ------
    >>> adata_to_h5(adata=adata,h5=h5, assay_name='RNA')
    >>>
    -----

    """
    adata_raw = adata.raw
    data = h5.create_group('data')
    var = h5.create_group('var')
    # --- save the data if adata.raw exists
    df_to_h5(df=adata.obs, h5=h5, gr_name='obs') # save the obs
    if not adata_raw is None:    
        if save_X:
            # save as X (scale)
            matrix_to_h5(mat=adata.X, h5=data, gr_name='X')
            df_to_h5(df=adata.var, h5=var, gr_name='X')
            # save as rawX (data)
            matrix_to_h5(mat=adata_raw.X, h5=data, gr_name='rawX')
            df_to_h5(df=adata_raw.var, h5=var, gr_name='rawX')
        else:
            # save as X (data)
            matrix_to_h5(mat=adata_raw.X, h5=data, gr_name='X')
            df_to_h5(df=adata_raw.var, h5=var, gr_name='X')
    else:
        matrix_to_h5(mat=adata.X, h5=data, gr_name='X')
        df_to_h5(df=adata.var,h5=var, gr_name='X')
    #--- save the dimension reduction
    if len(adata.obsm.keys())>0:
        dimR = h5.create_group('dimR')
        for k in [k for k in adata.obsm.keys()]:
            K = re.sub("^.*_", "", k).upper()
            dimR.create_dataset(K, data=adata.obsm[k], dtype=np.float32)
    if save_graph:
        
        gr = adata.obsp
        if len(gr.keys()) > 0:
            graphs = h5.create_group('graphs')
            gra_dict = {"distances": "knn", "connectivities": "snn"}
        #--- save the neighbor graphs
            for g in gra_dict.keys():
                matrix_to_h5(mat=gr[g], h5=graphs, gr_name=gra_dict[g])
    if assay_name == 'spatial':
        spatial_to_h5(adata=adata, h5=h5, gr_name=assay_name)
    # only save the uns color
    uns = h5.create_group('uns')
    for c in adata.uns_keys():
        if 'colors' in c:
            # uns.create_dataset(c, data=adata.uns[c])
            uns.create_dataset(c,data=np.array(adata.uns[c]).astype(np.object))
    # save the layers for the some data type, this dim is same as the X, and the varm gene same as the X
    if save_X:
        if len(adata.layers.keys())>0: 
            layers = h5.create_group('layers')
            for l in adata.layers.keys():
                matrix_to_h5(mat=adata.layers[l], h5=layers, gr_name=l)
        if len(adata.varm.keys())>0:
            varm = h5.create_group('varm')
            for j in adata.varm.keys():
                varm.create_dataset(j, data=adata.varm[j], dtype=np.float32)
    return
#--- To be continued



### pandas dataframe save to the h5 file
def df_to_h5(df: pd.DataFrame,
             h5: Union[h5py.File,h5py.Group],
             gr_name: Union[str, None] = None
             ) -> None:
    """
    pandas.core.frame.DataFrame be converted the h5 format that R can read in

    Parameters:
    ----------
    df : pandas.core.frame.Data.Frame
    h5 : h5py.File
    gr_name : the group name in the h5py.File 
    ----------

    Usage:
    -----
    >>> import PyIOH5
    >>> import h5py
    >>> h5 = h5py.File('test.h5', 'w')
    >>> PyIOH5.df_to_h5(df=df, h5=h5, gr_name = 'dataframe')
    >>> h5.close()
    -----
    """
    if gr_name not in h5.keys():
        h5df = h5.create_group(gr_name)
    else:
        h5df = h5[gr_name]
    cate_dict = {}
    df.index = df.index.astype(str)
    h5df.create_dataset(name='index', data=df.index.values.astype(h5py.special_dtype(vlen=str))) # rownames to str
    if len(df.columns)>0:
        dfcol = df.columns.copy()
        dfcol = dfcol.astype(str)
        h5df.create_dataset(name='colnames', data=dfcol.values.astype(h5py.special_dtype(vlen=str))) # colnames to str
    for k in df.keys():
        if is_categorical_dtype(df[k]):
            h5df.create_dataset(name=k, data=df[k].cat.codes.values)
            h5df[k].attrs['origin_dtype'] = 'category'
            cate_dtype = df[k].cat.categories.values.dtype
            if np.issubdtype(cate_dtype, np.integer):
                cate_dict[k] = df[k].cat.categories.values
            if np.issubdtype(cate_dtype, np.floating):
                cate_dict[k] = df[k].cat.categories.values
            if np.issubdtype(cate_dtype, np.object):
                cate_dict[k] = df[k].cat.categories.values.astype(h5py.special_dtype(vlen=str))
        if is_object_dtype(df[k]):
            str_to_cate = pd.Categorical(df[k].astype('str'))
            h5df.create_dataset(name=k, data=str_to_cate.codes)
            h5df[k].attrs['origin_dtype'] = 'string'
            cate_dict[k] = str_to_cate.categories.values.astype(h5py.special_dtype(vlen=str))
        if is_bool_dtype(df[k]):
            bool_to_int = df[k].astype(int)
            h5df.create_dataset(name=k, data=bool_to_int.values)
            h5df[k].attrs['origin_dtype'] = 'bool'
        if is_float_dtype(df[k]) or is_integer_dtype(df[k]):
            h5df.create_dataset(name=k, data=df[k].values)
            h5df[k].attrs['origin_dtype'] = 'number'
    if len(cate_dict.keys())>0:
        h5df_cate = h5df.create_group('category')
        for ca in cate_dict.keys():
            h5df_cate.create_dataset(names=ca, data=cate_dict[ca])
    return 
#     if gr_name not in h5.keys():
#         h5df = h5.create_group(gr_name)
#     else:
#         h5df = h5[gr_name]
#     df.index = df.index.astype(str)
#     h5df.create_dataset(name='index', data=df.index.values.astype(h5py.special_dtype(vlen=str))) # rownames to str
#     if len(df.columns)>0:
#         dfcol = df.columns.copy()
#         dfcol = dfcol.astype(str)
#         h5df.create_dataset(name='colnames', data=dfcol.values.astype(h5py.special_dtype(vlen=str))) # colnames to str
#     for k in df.keys():
#         if is_categorical_dtype(df[k]):
#             h5df.create_dataset(name=k, data=df[k].cat.codes.values)
#             h5df[k].attrs['origin_dtype'] = 'category'
#             cate_dtype = df[k].cat.categories.values.dtype
#             if np.issubdtype(cate_dtype, np.integer):
#                 h5df.create_dataset(name=k+'_levels', data=df[k].cat.categories.values)
#             if np.issubdtype(cate_dtype, np.floating):
#                 h5df.create_dataset(name=k+'_levels', data=df[k].cat.categories.values)
#             if np.issubdtype(cate_dtype, np.object):
#                 h5df.create_dataset(name=k+'_levels', data=df[k].cat.categories.values.astype(h5py.special_dtype(vlen=str)))
#         if is_object_dtype(df[k]):
#             str_to_cate = pd.Categorical(df[k].astype('str'))
#             h5df.create_dataset(name=k, data=str_to_cate.codes)
#             h5df[k].attrs['origin_dtype'] = 'string'
#             h5df.create_dataset(name=k+'_levels', data=str_to_cate.categories.values.astype(h5py.special_dtype(vlen=str)))
#         if is_bool_dtype(df[k]):
#             bool_to_int = df[k].astype(int)
#             h5df.create_dataset(name=k, data=bool_to_int.values)
#             h5df[k].attrs['origin_dtype'] = 'bool'
#         if is_float_dtype(df[k]) or is_integer_dtype(df[k]):
#             h5df.create_dataset(name=k, data=df[k].values)
#             h5df[k].attrs['origin_dtype'] = 'number'
#     return 

### matrix save to the h5 file
def matrix_to_h5(mat,
                 h5: Union[h5py.Group, h5py.File],
                 gr_name: Union[str, None] = None
                 ) -> None:
    """
    The matrix(scipy.sparse.csr.csr_matrix or np.ndarray) is converted to the matrix in h5 format or is stored into the h5 file that R can read.

    Parameters:
    ----------
    mat : scipy.sparse.csr.csr_matrix or numpy.ndarray
    h5 : h5py.File
    gr_name : the group name in the h5py.File 
    ----------

    Usage:
    -----
    >>> import PyIOH5
    >>> import h5py
    >>> from scipy import sparse 
    >>> indptr = np.array([0, 2, 3, 6])
    >>> indices = np.array([0, 2, 2, 0, 1, 2])
    >>> data = np.array([1, 2, 3, 4, 5, 6])
    >>> spm = sparse.csr_matrix((data, indices, indptr), shape=(3, 3))
    >>> h5 = h5py.File('test.h5', 'w')
    >>> PyIOH5.matrix_to_h5(mat = spm,h5 = h5,gr_name = 'sparsematrix')
    >>>
    -----
    """
    if gr_name not in h5.keys():
        h5mat = h5.create_group(gr_name)
    else:
        h5mat = h5[gr_name]
    if isinstance(mat, scipy.sparse.csr.csr_matrix):
        h5mat_i = h5mat.create_dataset("indices", data=mat.indices)
        h5mat_p = h5mat.create_dataset("indptr", data=mat.indptr)
        h5mat_x = h5mat.create_dataset("values", data=mat.data, dtype=np.float32)
        h5mat_dims = h5mat.create_dataset("dims", data=mat.shape)
        h5mat.attrs["datatype"] = "SparseMatrix"
    elif isinstance(mat, np.ndarray):
        h5mat_mat = h5mat.create_dataset("matrix", data=mat, dtype=np.float32)
        h5mat_dims = h5mat.create_dataset("dims", data=mat.shape)
        h5mat.attrs['datatype'] = 'Array'
    elif 'core' in dir(anndata):
        if isinstance(mat, anndata.core.views.SparseCSRView):
            h5mat_i = h5mat.create_dataset("indices", data=mat.indices)
            h5mat_p = h5mat.create_dataset("indptr", data=mat.indptr)
            h5mat_x = h5mat.create_dataset("values", data=mat.data, dtype=np.float32)
            h5mat_dims = h5mat.create_dataset("dims", data=mat.shape)
            h5mat.attrs["datatype"] = "SparseMatrix"
        elif isinstance(mat, anndata.core.views.ArrayView):
            h5mat_mat = h5mat.create_dataset("matrix", data=mat, dtype=np.float32)
            h5mat_dims = h5mat.create_dataset("dims", data=mat.shape)
            h5mat.attrs['datatype'] = 'Array'
    elif 'base' in dir(anndata):
        if isinstance(mat, anndata.base.ArrayView):
            h5mat_mat = h5mat.create_dataset("matrix", data=mat, dtype=np.float32)
            h5mat_dims = h5mat.create_dataset("dims", data=mat.shape)
            h5mat.attrs['datatype'] = 'Array'
        elif isinstance(mat, anndata.base.SparseCSRView):
            h5mat_i = h5mat.create_dataset("indices", data=mat.indices)
            h5mat_p = h5mat.create_dataset("indptr", data=mat.indptr)
            h5mat_x = h5mat.create_dataset("values", data=mat.data, dtype=np.float32)
            h5mat_dims = h5mat.create_dataset("dims", data=mat.shape)
            h5mat.attrs["datatype"] = "SparseMatrix"
    elif '_core' in dir(anndata):
        if isinstance(mat, anndata._core.views.ArrayView):
            h5mat_mat = h5mat.create_dataset("matrix", data=mat, dtype=np.float32)
            h5mat_dims = h5mat.create_dataset("dims", data=mat.shape)
            h5mat.attrs['datatype'] = 'Array'
        elif isinstance(mat, anndata._core.views.SparseCSRView):
            h5mat_i = h5mat.create_dataset("indices", data=mat.indices)
            h5mat_p = h5mat.create_dataset("indptr", data=mat.indptr)
            h5mat_x = h5mat.create_dataset("values", data=mat.data, dtype=np.float32)
            h5mat_dims = h5mat.create_dataset("dims", data=mat.shape)
            h5mat.attrs["datatype"] = "SparseMatrix"
    else:
        raise TypeError("The adata.X version is not supported")
    return


def spatial_to_h5(adata,h5,gr_name = 'spatial'):
    """
    The spatial messages are converted to the into the h5 file that R can read.

    Parameters:
    ----------
    adata: anndata.AnnData
    h5 : h5py.File
    gr_name : The group name in the h5py.File. Default is 'spatial'
    ----------

    Usage:
    -----
    >>> spatial_to_h5(adata=adata, h5=h5, gr_name='spatial')
    >>>
    -----
    """
    sp = h5.create_group('spatial')
    for sampleid in adata.uns[gr_name].keys():
        sid_h5 = sp.create_group(sampleid)
        #--- save tissue image
        sid_image_h5 = sid_h5.create_group('image')
        simage = adata.uns[gr_name][sampleid]['images']
        for im in simage.keys():
            sid_image_h5.create_dataset(im, data=simage[im])
        #--- save tissue coordinate
        v1 = ['in_tissue','array_row','array_col']
        df = adata.obs[v1]
        coor_df = pd.concat([df,pd.DataFrame(adata.obsm['spatial'],index = df.index, columns=['image_1', 'image_2'])],axis=1)
        df_to_h5(df = coor_df, h5 = sid_h5, gr_name = 'coor')
        #--- save the scalefactor
        sid_scalefactor_h5 = sid_h5.create_group('scalefactors')
        sf = adata.uns[gr_name][sampleid]['scalefactors']
        for k in sf.keys():
            sid_scalefactor_h5.create_dataset(k, data=sf[k])
    return   

def write_rds(adata: Union[str, None] = None,
	          file: Union[str, None] = None,
             object_type:str = 'seurat',
             assay_name: str = 'RNA'
            ) -> None:
    rfile = re.sub('.rds','_tmp.h5',file)
    write_h5(adata=adata, file=rfile, assay_name=assay_name)
    current_path = os.path.abspath(__file__)
    diorc_file= os.path.abspath(os.path.dirname(current_path) + os.path.sep + ".") + '/R/diorC.R'
    os.system('Rscript ' + diorc_file +' -r '+ rfile +' -t '+ object_type + ' -a '+assay_name)
    return 

## to be continue




