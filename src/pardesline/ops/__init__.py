"""The algorithms, one script per method, grouped by module.

Every script follows the same contract and can be run directly:

    python -m pardesline.ops.point_cloud_processing.voxel_downsample \\
        --input scan.ply --output small.ply --voxel_size 0.02

``--input`` and ``--output`` are files; two-input methods add ``--moving``;
every other flag is a parameter declared in the catalog. Exit code 0 means
the output was written. Prefer :func:`pardesline.run` from Python: it
validates parameters, picks an output path and captures the log.
"""
