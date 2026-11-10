import random
import os
import pdfplumber
from PIL import Image

# Fixed seed
SEED = 42
random.seed(SEED)

from populate_sources_hbns import hbns_sources
from populate_sources_elm import elm_sources

all_sources = hbns_sources + elm_sources

# Sample 10 sources
sampled_indices = sorted(random.sample(range(len(all_sources)), 10))
sampled_sources = [all_sources[i] for i in sampled_indices]

print(f"Sampled {len(sampled_sources)} sources with seed {SEED}:")
for idx, s in enumerate(sampled_sources, 1):
    print(f"#{idx:02d}: [{s['entity']}] {s['source_name']} ({s['module']}) - Activity: {s['activity_data']} {s['activity_unit']} - CO2e: {s['rep_co2e']}")
