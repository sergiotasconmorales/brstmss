import pandas as pd
import numpy as np
from sklearn import preprocessing

CONTOUR_FEATURES_TAGS =\
    ['solidity',
     'convex_area',
     'rectangularity',
     'eccentricity',
     'center_of_gravity_x',
     'center_of_gravity_y',
     'circularity_ratio',
     'min_axis_length',
     'max_axis_length',
     'ellipse_variance']


def __unfold_features(list_of_features):

    new_feature_list = [None] * len(list_of_features)
    position = 0
    for dictionary in list_of_features:
        new_dictionary = dict()
        headers =\
            {'File name': dictionary.get("File name"),
             'Contour': dictionary.get("Contour"),
             'Layer': dictionary.get("Layer")}
        new_dictionary.update(headers)
        contour = dict(zip(CONTOUR_FEATURES_TAGS, dictionary.get("Contour features")))
        new_dictionary.update(contour)
        hlfeatures = dictionary.get("Haralick Features")
        hlfeatures = dict(zip(["hf_" + str(val) for val in range(1, hlfeatures.shape[0])], hlfeatures))
        new_dictionary.update(hlfeatures)
        humoments = dictionary.get("Hu moments")
        humoments = dict(zip(["hu_" + str(val) for val in range(1, humoments.shape[0])], humoments))
        new_dictionary.update(humoments)
        tas = dictionary.get("TAS features").flatten()
        tas = dict(zip(["tas_" + str(val) for val in range(1, tas.shape[0])], tas))
        new_dictionary.update(tas)
        lbp = dictionary.get("lbp").flatten()
        lbp = dict(zip(["lbp_" + str(val) for val in range(1, lbp.shape[0])], lbp))
        new_dictionary.update(lbp)
        new_feature_list[position] = new_dictionary
        position += 1

    return new_feature_list


def create_entry(path_name, slice_counter, roi_counter, cnt_features, textures, hu_moments, lbp, tas_features, contour, layer):
    dictionary = {
        'File name': path_name,
        'Slice': slice_counter,
        'Roi number': roi_counter,
        'Contour features': cnt_features,
        'Haralick Features': textures,
        'Hu moments': hu_moments,
        'lbp': lbp,
        'TAS features': tas_features,
        'Contour': contour,
        'Layer': layer
    }

    return dictionary


def create_features_dataframe(list_of_features):
    dataframe = __unfold_features(list_of_features)
    dataframe = pd.DataFrame(dataframe)
    tags = dataframe[['File name', 'Layer', 'Contour']]
    dataframe = dataframe.drop(['File name', 'Layer', 'Contour'], axis=1)
    return [dataframe, tags]


def drop_unwanted_features(dataframe):

    dataframe = dataframe.drop("center_of_gravity_x", axis=1)
    dataframe = dataframe.drop("center_of_gravity_y", axis=1)
    return dataframe

def normalize_dataframe(dataframe):
    dataframe =\
        pd.DataFrame(
            np.transpose(preprocessing.normalize(dataframe.T)),
            columns=dataframe.columns,
            index=dataframe.index)
    return dataframe
