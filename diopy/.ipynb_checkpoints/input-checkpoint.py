# -*- coding: utf-8 -*-
"""
Created on Fri Sep 27 23:23:03 2019

@author: fenghuijian

Introduction: We use the Hierarchical Data Format V5(hdf5) file for data transmission between Python platform and R platform,
so as to achieve the purpose of reading data quickly and conveniently.Below, we will abbreviate hdf5 as h5.
"""

###  import the packages
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

### adata read h5 file 
def read_h5(file: Union[str, None] = None,
            assay_name: str = 'RNA'
            ) -> anndata.AnnData:
    """
    
    The h5 file will be converted to the anndata.AnnData object

    Parameters:
    ----------
    file : The h5 file
    assy_name : Denotes which omics data to save. Default is 'RNA'. Available options are:
                'RNA': means that this omics data is scRNA-seq data
                'spatial': means that this omics data is spatial data generated by 10x Genomics Visium toolkits
                
    return anndata.AnnData
    ----------

    Usage:
    ------
    >>> import diopy
    >>> adata = diopy.input.read_h5(file='scdata.h5')
    -----

    """
    if file is None:
        raise OSError('No such file or directory')
    h5 = h5py.File(name=file, mode='r')
    try:
        adata = h5_to_adata(h5=h5, assay_name=assay_name)
    except Exception as e:
        print('Error:', e)
    finally:
        h5.close()
    return adata

### h5 file convert to the matrix 
def h5_to_matrix(h5mat: [h5py.Group, h5py.File]
                 ) -> Union[scipy.sparse.csr.csr_matrix, np.ndarray]:
    """

    The h5 group will be  converted to the scipy.sparse.csr.csr_matrix or numpy.ndarray

    Parameters:
    ----------
    h5mat : The h5py.Group saving the matrix
    
    return scipy.sparse.csr.csr_matrix or numpy.ndarray
    ----------

    Usage:
    ------
    >>> import diopy
    >>> import h5py
    >>> h5 = h5py.File('scdata.h5', 'r')
    >>> mtx = diopy.input.h5_to_matrix(h5mat=h5['data/X'])
    >>> h5.close()
    >>>
    -----

    """
    if isinstance(h5mat.attrs['datatype'], str):
        if h5mat.attrs['datatype'] == 'SparseMatrix':
            x = h5mat["values"][()].astype(np.float32)
            indices = h5mat["indices"][()]
            indptr = h5mat["indptr"][()]
            shapes = h5mat["dims"][()]
            mat = sparse.csr_matrix((x, indices, indptr), shape=shapes, dtype=np.float32)
        elif h5mat.attrs['datatype'] == 'Array':
            mat = h5mat['matrix'][()].astype(np.float32)
    elif isinstance(h5mat.attrs['datatype'], np.ndarray):
        if h5mat.attrs['datatype'].astype('str').item() == 'SparseMatrix':
            x = h5mat["values"][()].astype(np.float32)
            indices = h5mat["indices"][()]
            indptr = h5mat["indptr"][()]
            shapes = h5mat["dims"][()]
            mat = sparse.csr_matrix((x, indices, indptr), shape=shapes, dtype=np.float32)
        elif h5mat.attrs['datatype'].astype('str').item() == 'Array':
            mat = h5mat['matrix'][()].astype(np.float32)
    return mat


### h5 file to the pandas dataframe
def h5_to_df(h5df: [h5py.Group,h5py.File]
             ) -> pd.DataFrame:
    """

    The h5 group will be converted to the pandas.dataframe

    Parameters:
    ----------
    h5df: The h5py.Group saving the dataframe 
    
    return pandas.core.frame.DataFrame
    ----------

    Usage:
    ------
    >>> import diopy
    >>> import h5py
    >>> h5 = h5py.File('scdata.h5', 'r')
    >>> df = diopy.input.h5_to_df(h5df=h5['obs'])
    >>> h5.close()
    >>>
    -----

    """
    to_dict = {}
    to_dict['index'] = h5df['index'][()].astype(str).astype(np.object)
    for i in h5df.keys():
        if(len(h5df[i].attrs.keys())>0):
            if np.array(h5df[i].attrs['origin_dtype']).astype(str).astype(np.object) == 'category':
                e0 = h5df[i][()].astype(int)
                if np.min(e0) == -2147483648:
                    e0[e0==-2147483648] = -1
                lvl = h5df['category'][i][()].astype(str).astype(np.object)
                # to_dict[i] = pd.Categorical(values=lvl[e0],categories=lvl)
                lvl =  pd.CategoricalDtype(lvl)
                to_dict[i] = pd.Categorical.from_codes(codes=e0, dtype=lvl)
            if np.array(h5df[i].attrs['origin_dtype']).astype(str).astype(np.object) == 'string':
                e0 = h5df[i][()].astype(int)
                if np.min(e0) == -2147483648:
                    e0[e0==-2147483648] = -1
                lvl = h5df['category'][i][()].astype(str).astype(np.object)
                # to_dict[i] = pd.Categorical(values=lvl[e0],categories=lvl).astype(np.object)
                lvl =  pd.CategoricalDtype(lvl)
                to_dict[i] = pd.Categorical.from_codes(codes=e0, dtype=lvl)
            if np.array(h5df[i].attrs['origin_dtype']).astype(str).astype(np.object) == 'bool':
                e0 = h5df[i][()].astype(int)
                to_dict[i] = e0.astype(np.bool)
            if np.array(h5df[i].attrs['origin_dtype']).astype(str).astype(np.object) == 'number':
                e0 = h5df[i][()]
                to_dict[i] = e0
    df= pd.DataFrame(to_dict)
    df.set_index('index', inplace=True)
    if 'colnames' in h5df.keys():
        cnames = h5df['colnames'][()].astype(str).astype(np.object)
        df = df[cnames]
    return df


def h5_to_spatial(h5spa):
    """

    The h5 group will be converted to the spatial messages including image, scalefactor and coordinate.
    
    Parameters:
    ----------
    h5df: The h5py.Group saving the spatial messages 
    
    return the dict including the spatial messages
    ----------

    Usage:
    ------
    >>> import diopy
    >>> import h5py
    >>> h5 = h5py.File('scdata.h5', 'r')
    >>> spatial = diopy.input.h5_to_spatial(h5spa=h5['spatial'])
    >>> h5.close()
    >>>
    -----

    """
    spatial_dict = {}
    for sid in h5spa.keys():
        spatial_sid_dict = {}
        sid_h5 = h5spa[sid]
        for me in sid_h5.keys():
            if ('image' in me) or ('images' in me):
                im_dict = {}
                for im in sid_h5[me]:
                    im_dict[im] = sid_h5[me][im][()]
                spatial_sid_dict['images'] = im_dict
            if 'scalefactors' in me:
                sf_dict = {}
                for sf in sid_h5[me]:
                    sf_v = sid_h5[me][sf][()]
                    if isinstance(sf_v, np.ndarray):
                        sf_dict[sf] = sf_v[0]
                    else:
                        sf_dict[sf] = sf_v
                spatial_sid_dict[me] = sf_dict
            if 'coor' in me:
                spatial_sid_dict['coor'] = h5_to_df(sid_h5[me])
        spatial_dict[sid] = spatial_sid_dict
    return spatial_dict


def to_obs_(h5):
    """

    The h5 group 'obs' will be converted pandas.core.frame.DataFrame
    
    Parameters:
    ----------
    h5: The h5py.File
    
    return The pandas.core.frame.DataFrame representing 'obs'
    ----------

    """
    to_obs = h5_to_df(h5df = h5['obs'])
    return(to_obs)

def to_dimr_(h5):
    """

    The h5 group 'dimR' will be converted dictionary-like object
    
    Parameters:
    ----------
    h5: The h5py.File
    
    return The dict repesenting 'dimension reduction'
    ----------

    """
    dimR=h5['dimR']
    to_dimr = {}
    for k in dimR.keys():
        if k == 'SPATIAL':
            to_dimr['spatial'] = dimR[k][()]
        else:
            X_k = "X_" + k.lower()
            to_dimr[X_k] = dimR[k][()]
    return(to_dimr)

def to_spatial_(h5):
    """

    The h5 group 'spaitial' will be converted dictionary-like object
    
    Parameters:
    ----------
    h5: The h5py.File
    
    return The dict repesenting 'spatial'
    ----------

    """
    to_spatial = h5_to_spatial(h5spa=h5['spatial'])
    return(to_spatial)

def to_data_(h5):
    """

    The h5 group 'data' will be converted dictionary-like object
    
    Parameters:
    ----------
    h5: The h5py.File
    
    return The dict repesenting 'X' and 'raw.X'
    ----------

    """
    data = h5['data']
    to_data = {}
    for d in data.keys():
        to_data[d] = h5_to_matrix(h5mat=data[d])
    return(to_data)

def to_var_(h5):
    """

    The h5 group 'var' will be converted pandas.core.frame.DataFrame
    
    Parameters:
    ----------
    h5: The h5py.File
    
    return The dict repesenting 'var'
    ----------

    """
    to_var = {}
    var=h5['var']
    for v in var.keys():
        to_var[v] = h5_to_df(h5df=var[v])
    return(to_var)

def to_graphs_(h5):
    """

    The h5 group 'graphs' will be converted dictionary-like object
    
    Parameters:
    ----------
    h5: The h5py.File
    
    return The dict repesenting 'graphs'
    ----------

    """
    to_graphs = {}
    graphs = h5['graphs']
    neig = {"knn": "distances", "snn": "connectivities"}
    for g in neig.keys():
        to_graphs[neig[g]] = h5_to_matrix(h5mat=graphs[g])
    return(to_graphs)

def to_layers_(h5):
    """

    The h5 group 'layers' will be converted dictionary-like object
    
    Parameters:
    ----------
    h5: The h5py.File
    
    return The dict repesenting 'layers'
    ----------

    """
    to_layers = {}
    layers = h5['layers']
    for l in layers.keys():
        to_layers[l] = h5_to_matrix(h5mat=layers[l])
    return(to_layers)

def to_varm_(h5):
    """

    The h5 group 'varm' will be converted dictionary-like object
    
    Parameters:
    ----------
    h5: The h5py.File
    
    return The dict repesenting 'varm'
    ----------

    """
    to_varm = {}
    varm = h5['varm']
    for v in varm.keys():
        to_varm[v] = varm[v][()]
    return(to_varm)

def to_uns_(h5):
    """

    The h5 group 'uns' will be converted dictionary-like object
    
    Parameters:
    ----------
    h5: The h5py.File
    
    return The dict repesenting 'uns'
    ----------

    """
    to_uns = {}
    uns = h5['uns']
    for u in uns.keys():
        to_uns[u] = uns[u][()]
    return(to_uns)

def switch(h5key, h5):
    """

    The switch function
    
    Parameters:
    ----------
    h5: The h5py.File
    h5keys: The keys of h5py.File
    
    return all object of existing h5 group
    ----------

    """
    swi = {'data':to_data_, 
           'obs':to_obs_,
           'var':to_var_,
           'dimR':to_dimr_,
           'spatial':to_spatial_,
           'graphs':to_graphs_,
           'layers':to_layers_,
           'uns':to_uns_,
           'varm':to_varm_}
    method = swi.get(h5key)
    return(method(h5))



# def h5_to_dict(h5):
#     adata_dict= {}
#     for i in h5.keys():
#         if i == 'obs':
#             adata_dict[i] = h5_to_df(h5[i])
#         if i == 'dimR':
#             dimR=h5[i]
#             dimR_dict = {}
#             for k in dimR.keys():
#                 if k == 'SPATIAL':
#                     dimR_dict['spatial'] = dimR[k][()]
#                 else:
#                     X_k = "X_" + k.lower()
#                     dimR_dict[X_k] = dimR[k][()]
#                 adata_dict[i] = dimR_dict
#         if i == 'spatial':
#                 adata_dict[i] = h5_to_spatial(h5spa=h5[i])
#         if i == 'data':
#             data=h5[i]
#             for d in data.keys():
#                 adata_dict[d] = h5_to_matrix(h5mat=data[d])
#         if i == 'var':
#             var_dict = {}
#             var=h5[i]
#             for v in var.keys():
#                 var_dict[v] = h5_to_df(h5df=var[v])
#             adata_dict[i] = var_dict
#         if i == 'graphs':
#             graph_dict={}
#             graph = h5[i]
#             neig = {"knn": "distances", "snn": "connectivities"}
#             for g in neig.keys():
#                 graph_dict[neig[g]] = h5_to_matrix(h5mat=graph[g])
#             adata_dict[i] = graph_dict
#         if i == 'layers':
#             layer_dict = {}
#             layer=h5[i]
#             for l in layer.keys():
#                 layer_dict[l] = h5_to_matrix(h5mat=layer[l])
#             adata_dict[i] = layer_dict
#         if i == 'varm':
#             varm_dict = {}
#             varm = h5[i]
#             for v in varm.keys():
#                 varm_dict[v] = varm[v][()]
#             adata_dict[i] = varm_dict
#         if i == 'uns':
#             uns_dict = {}
#             u
#     return adata_dict


### h5 file convert to the h5 file 
def h5_to_adata(h5: h5py.File = None,
                assay_name: Union[str, None] = None
                ) -> anndata.AnnData:
    """

    The h5 file be converted to anndata.AnnData

    Parameters:
    ----------
    h5 : The h5 file
    assy_name : Denotes which omics data to save. Default is 'RNA'. Available options are:
        'RNA': means that this omics data is scRNA-seq data
        'spatial': means that this omics data is spatial data generated by 10x Genomics Visium toolkits
    
    return anndata.AnnData
    ----------

    Usage:
    ------
    >>> import diopy
    >>> import h5py
    >>> h5 = h5py.File('scdata.h5', 'r')
    >>> adata = diopy.input.h5_to_adata(h5=h5, assay_name='RNA')
    >>> h5.close()
    >>>

    -----

    """
    assayname = np.array(h5.attrs['assay_name'].astype('str').tolist(), dtype=np.object)
    adata_dict = {}
    #--- obs,var,rawData,nomData, dimR read into the python
    if assayname == np.array([assay_name]):
        adata_dict = {}
        for h5key in h5.keys():
            adata_dict[h5key] = switch(h5key, h5)
        # adata_dict = h5_to_dict(h5=h5)
        if (np.isin(['X','rawX'],list(adata_dict['data'].keys()))).all():
            adata = anndata.AnnData(X=adata_dict['data']['X'], obs=adata_dict['obs'], var=adata_dict['var']['X'])
            adata_raw = anndata.AnnData(X=adata_dict['data']['rawX'], obs=adata_dict['obs'], var=adata_dict['var']['rawX'])
            adata.raw = adata_raw
        else:
            adata = anndata.AnnData(X=adata_dict['data']['X'], obs=adata_dict['obs'], var=adata_dict['var']['X'])
        if 'dimR' in adata_dict.keys():
            adata.obsm = adata_dict['dimR']
        if 'graphs' in adata_dict.keys():
            adata.obsp = adata_dict['graphs']
        if 'layers' in adata_dict.keys():
            for l in adata_dict['layers'].keys():
                if adata.X.shape == adata_dict['layers'][l].shape:
                    adata.layers[l] = adata_dict['layers'][l]
        if 'varm' in adata_dict.keys():
            adata.varm = adata_dict['varm']
        if 'uns' in adata_dict.keys():
            adata.uns = adata_dict['uns']
        if assay_name == 'spatial':
            v1 = ['in_tissue','array_row','array_col']
            for spk in adata_dict[assay_name].keys():
                obs_sp = pd.concat([adata_dict[assay_name][spk]['coor'][v1], adata.obs[adata.obs.columns[~adata.obs.columns.isin(v1)]]], axis=1)
                adata.obs = obs_sp
                adata.obsm[assay_name] = adata_dict[assay_name][spk]['coor'][['image_1','image_2']].values
                del adata_dict[assay_name][spk]['coor']
                adata.uns[assay_name] = adata_dict[assay_name]
    else:
        raise OSError("Please provide the correct assay_name")
    return adata


# read the R rds file 
def read_rds(file: Union[str, None] = None,
             object_type:str = 'seurat',
             assay_name: str = 'RNA'
            ) -> anndata.AnnData:
    """

    The rds file will be converted to the anndata.AnnData

    Parameters:
    ----------
    file : The rds file
    object_type: Denotes which object saved into the rds file. Default is 'seurat'. Available options are:
        'seurat': The Seurat object
        'singlecellexperiment': The SingleCellExperiment object
    assy_name : Denotes which omics data to save. Default is 'RNA'. Available options are:
        'RNA': means that this omics data is scRNA-seq data
        'spatial': means that this omics data is spatial data generated by 10x Genomics Visium toolkits
    
    return anndata.AnnData
    ----------

    Usage:
    ------
    >>> import diopy
    >>> adata = diopy.input.read_rds(file='scdata.rds', assay_name='RNA', object_type='seurat')
    >>>

    -----

    """
    # osr = os.path.join(os.path.dirname(__file__), '/R/diopyR.R')
    current_path = os.path.abspath(__file__)
    diopyr_file= os.path.abspath(os.path.dirname(current_path) + os.path.sep + ".") + '/R/diopyR.R'
    os.system('Rscript ' + diopyr_file +' -r '+ file +' -t '+ object_type)
    tmp = re.sub('.rds', '_tmp.h5', file)
    adata = read_h5(file =tmp, assay_name = assay_name)
    return adata

#--- To be continues
