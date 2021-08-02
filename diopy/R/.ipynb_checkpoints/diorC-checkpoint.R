library(getopt)
library(dior)
spec <- matrix(
  c('readfile','r',1,'character','Reading the h5 file',
    'targetobject', 't',1,'character','The single-cell data object which supprots Seurat and SingleCellExperiment',
    'assay_name','a',1,'character','The primary data types, such as scRNA data or spatial data'
  ),
  byrow = TRUE, ncol =5
)
opt <- getopt(spec)
# read the rds file
data <- read_h5(file = opt$readfile, assay.name = opt$assay_name, target.object = opt$targetobject)
saveRDS(data, file = gsub('_tmp.h5', '.rds', opt$readfile))
