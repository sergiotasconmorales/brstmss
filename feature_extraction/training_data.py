from os.path import join
import pandas as pd
import numpy as np
import cv2
from main_flow.flow import process_single_image
from .build_features_file import read_images
from evaluation.dice_similarity import dice_similarity
import progressbar
from main_flow.split_features import create_features_dataframe, drop_unwanted_features, normalize_dataframe

def __get_optimal_dice(roi_mask, gts):

    values = np.zeros([len(gts), 1])
    for idx in range(0, len(gts)):
        dice, _ = dice_similarity(roi_mask, gts[idx])
        values[idx] = dice

    return 0 if len(values) == 0 else values.max()


def label_findings(gt_path, filename, features, groundtruths_filenames):
    labels = np.zeros([len(features)])
    dices = np.zeros([len(features)])

    # Labelled as Zero for non-masses, and 1 for masses

    # if the image doesn't have any groundtruth, we label the found masses as false positives.

    if filename not in groundtruths_filenames:
        return [labels, dices]

    gt_index = groundtruths_filenames.index(filename)
    # Dilate to remove holes in the GT
    gt = cv2.imread(join(gt_path, groundtruths_filenames[gt_index]), 0)
    kernel = np.ones((51, 51), np.uint8)
    gt = cv2.morphologyEx(gt, cv2.MORPH_OPEN, kernel, iterations=1)

    _, contours, _ = cv2.findContours(gt, cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE)

    gt_layers = []

    # Separate each gt mass in different layers
    for contour in contours:
        gt_mask = np.zeros_like(gt)
        cv2.drawContours(gt_mask, [contour], 0, 1, -1)
        gt_layers.append(gt_mask)

    index = 0
    for roi in features:
        roi_mask = np.zeros_like(gt)
        contour = roi.get("Contour")
        cv2.drawContours(roi_mask, [contour], 0, 1, -1)
        dice = __get_optimal_dice(roi_mask, gt_layers)
        dices[index] = dice

        # Positive if the Dice index is greater than 0.2
        labels[index] = 1 if dice > 0.2 else 0
        index += 1

    return [labels, dices]


def __get_features_and_classify(dataset_path, images_name):
    [raw_im_path, gt_im_path, _, gt_images, _, _] = read_images(dataset_path)

    total_labels = []
    total_features = []
    total_dices = []
    total_images = len(images_name)

    bar = progressbar.ProgressBar(maxval=total_images, widgets=[progressbar.Bar('=', '[', ']'), ' ', progressbar.Percentage()])
    bar.start()
    for img_counter in range(0, total_images):
        print("Processing img " + str(img_counter) + " of " + str(total_images))
        [_, features, _] =\
            process_single_image(raw_im_path, images_name[img_counter])
        [labels, dices] = label_findings(gt_im_path, images_name[img_counter], features, gt_images)
        total_features.extend(features)
        total_dices.extend(dices)
        total_labels.extend(labels)
        bar.update(img_counter + 1)

    bar.finish()

    return [total_labels, total_features, total_dices]


def partition_data(dataset_path):
    [raw_im_path, gt_im_path, raw_images, gt_images, _, _] = read_images(dataset_path)

    images_with_masses = list(set(raw_images) & set(gt_images))
    images_without_masses = list(set(raw_images) - set(gt_images))

    np.random.seed(42)

    # Choose proper dataset: 75% images with masses are for training while 25% for testing
    # 80% images without masses for training while 20% for testing

    index_imgs_with_masses= np.arange(len(images_with_masses))
    index_imgs_without_masses = np.arange(len(images_without_masses))
    images_with_masses_train =\
        np.array(np.random.choice(index_imgs_with_masses,np.uint(0.75*len(index_imgs_with_masses)),replace=False))
    images_without_masses_train =\
        np.array(np.random.choice(index_imgs_without_masses,np.uint(0.8*len(index_imgs_without_masses)),replace=False))

    # GET THE TRAINING SET:
    training_images_with_masses = [images_with_masses[i] for i in images_with_masses_train]
    training_images_without_masses = [images_without_masses[i] for i in images_without_masses_train]

    # GET THE TESTING SET:
    testing_images_with_masses = list(set(images_with_masses) - set(training_images_with_masses))
    testing_images_without_masses = list(set(images_without_masses) - set(training_images_without_masses))

    return [training_images_with_masses, training_images_without_masses, testing_images_with_masses, testing_images_without_masses]


def prepate_datasets(dataset_path):

    [training_images_with_masses, training_images_without_masses, testing_images_with_masses, testing_images_without_masses] =\
        partition_data(dataset_path)

    training = training_images_with_masses + training_images_without_masses
    testing = testing_images_with_masses + testing_images_without_masses

    print("Preparing training set!\n")
    [training_labels, training_features, training_dices] = __get_features_and_classify(dataset_path, training)

    [df_features, tags] = create_features_dataframe(training_features)
    training_features = 0
    classes_and_dices = pd.DataFrame(np.array([training_labels, training_dices]).transpose(), columns=["Class", "Dice"])
    tags = pd.concat([tags, classes_and_dices], axis=1)
    df_features = drop_unwanted_features(df_features)
    #df_features = normalize_dataframe(df_features)

    df_features.to_csv(join(dataset_path, "training.csv"))
    tags.to_csv(join(dataset_path, "training_metadata.csv"))
    df_features = 0
    tags = 0


    print("Preparing testing set!\n")
    [testing_labels, testing_features, testing_dices] = __get_features_and_classify(dataset_path, testing)
    [df_features, tags] = create_features_dataframe(testing_features)
    testing_features = 0
    classes_and_dices = pd.DataFrame(np.array([testing_labels, testing_dices]).transpose(), columns=["Class", "Dice"])
    tags = pd.concat([tags, classes_and_dices], axis=1)
    df_features = drop_unwanted_features(df_features)
    # df_features = normalize_dataframe(df_features)

    df_features.to_csv(join(dataset_path, "testing.csv"))
    tags.to_csv(join(dataset_path, "testing_metadata.csv"))