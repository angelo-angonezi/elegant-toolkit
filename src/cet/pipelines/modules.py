# modules module

# Code destined to storing modules
# base commands for use in pipelines.

######################################################################
# defining commands

convert_images_modules = {'.ics': 'cet.preprocessing.converters.ics_to_tif',
                          '.nd2': 'cet.preprocessing.converters.nd2_to_tif',
                          '.tif': 'cet.preprocessing.converters.tif_to_tif',
                          '.vsi': 'cet.preprocessing.converters.vsi_to_tif'}
split_channels_module = 'cet.preprocessing.split_channels'
preprocess_images_module = 'cet.preprocessing.preprocess_images'
crop_images_module = 'cet.preprocessing.crop_images'
deconvolve_images_module = 'cet.preprocessing.deconvolve_images'
create_psfs_module = 'cet.preprocessing.create_psfs'
pad_images_module = 'cet.preprocessing.pad_images'
gaussian_blur_module = 'cet.preprocessing.filters.gaussian_blur'
difference_of_gaussians_module = 'cet.preprocessing.filters.difference_of_gaussians'
generate_binary_masks_module = 'cet.segmentation.generate_binary_masks'
generate_segmentation_masks_module = 'cet.segmentation.generate_segmentation_masks'
run_cellpose_module = 'cet.segmentation.run_cellpose'
optimize_bit_depth_module = 'cet.preprocessing.optimize_bit_depth'
close_masks_module = 'cet.segmentation.close_masks'
merge_masks_module = 'cet.segmentation.merge_masks'
resize_masks_module = 'cet.segmentation.resize_masks'
apply_masks_module = 'cet.segmentation.apply_masks'
generate_objects_dfs_module = 'cet.dataframes.generate_objects_dfs'
generate_pseudoembryos_df_module = 'cet.dataframes.generate_pseudoembryos_df'
join_dfs_module = 'cet.dataframes.join_dfs'
filter_df_module = 'cet.dataframes.filter_df'
generate_summary_dfs_module = 'cet.dataframes.generate_summary_dfs'
generate_cilia_summary_df_module = 'cet.dataframes.generate_cilia_summary_df'
normalize_summary_dfs_module = 'cet.dataframes.normalize_summary_dfs'
generate_pairwise_distances_dfs_module = 'cet.dataframes.generate_pairwise_distances_dfs'
generate_mask_distances_df_module = 'cet.dataframes.generate_mask_distances_df'
generate_dots_distances_df_module = 'cet.dataframes.generate_dots_distances_df'
summary_to_cescale_df_module = 'cet.dataframes.converters.summary_to_cescale_df'
generate_lineages_df_module = 'cet.dataframes.generate_lineages_df'
generate_lineage_summary_df_module = 'cet.dataframes.generate_lineage_summary_df'
plot_lineage_tree_module = 'cet.plots.plot_lineage_tree'
run_cescale_module = 'cet.lineage.run_cescale'

######################################################################
# end of current module
