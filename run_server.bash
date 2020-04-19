#!/bin/bash
source /usr/local/anaconda3/etc/profile.d/conda.sh
conda activate covid19graphs
bokeh serve --show covid19 --port 80