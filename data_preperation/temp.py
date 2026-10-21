import os
import pandas as pd

# Define root directory
root_directory = "/Users/abhilashchenreddy/PycharmProjects/BSI/data_preperation/Input/"
zips_file_path = os.path.join(root_directory, 'Zip_FIPS_Mapping.csv')
zips = pd.read_csv(zips_file_path)

# Standardize ZIP in Zip_fips_lookup
zips['ZIP'] = zips['ZIP'].astype(str).str.zfill(5).astype(int)
zips['STCOUNTYFP'] = zips['STCOUNTYFP'].astype(str).str.zfill(5).astype(int)
print(zips.shape)
print(zips[zips.ZIP == 30233])
zips = zips.drop_duplicates(subset=['ZIP'], keep='first')
print(zips.shape)
print(zips[zips.ZIP == 30233])

