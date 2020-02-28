import cv2
import time
import pickle

from detectnet import get_detectnet_config, get_detectnet_model, get_image_bounding_boxes
from rootnet import get_input, set_rootnet_config, get_rootnet_model, get_root
from posenet import set_posenet_config, get_posenet_model, get_pose
from config import cfg as pipeline_cfg
from util import load, to_csv, get_frames
from vis import visualize_and_save

def main():
    detectnet_config = get_detectnet_config()
    detectnet_model = get_detectnet_model(detectnet_config)
    set_rootnet_config()
    rootnet_model = get_rootnet_model()
    set_posenet_config()
    posenet_model = get_posenet_model()

    if pipeline_cfg.is_video:
        video = cv2.VideoCapture(pipeline_cfg.input_video_path)

        posenet_preds_list = []

        frames = get_frames(video)

        start = time.time()
        for i, image in enumerate(frames):
            print(str(i + 1) + " / " + str(len(frames)))
            person_boxes = get_image_bounding_boxes(image, detectnet_model)
            print(len(person_boxes))
            if len(person_boxes) == 0:
                continue
            person_images, k_values = get_input(image, person_boxes)
            rootnet_preds = get_root(image, person_boxes, rootnet_model, person_images, k_values)
            posenet_preds = get_pose(image, person_boxes, posenet_model, person_images, rootnet_preds)
            posenet_preds_list.append(posenet_preds)
        print("It takes ", str(time.time() - start) + " s")

        output_file = open(pipeline_cfg.output_video_binary_path, "wb")
        pickle.dump(posenet_preds_list, output_file)
        output_file.close()
        to_csv(pipeline_cfg.output_video_binary_path, pipeline_cfg.output_video_csv_path)

    else:
        image = cv2.imread(pipeline_cfg.input_image_path)
        from detectron2.engine import DefaultPredictor
        person_boxes = get_image_bounding_boxes(image, DefaultPredictor(detectnet_config))
        if len(person_boxes) == 0:
            return

        person_images, k_values = get_input(image, person_boxes)
        rootnet_preds = get_root(image, person_boxes, rootnet_model, person_images, k_values)
        # print(rootnet_preds)
        posenet_preds = get_pose(image, person_boxes, posenet_model, person_images, rootnet_preds)
        print(posenet_preds)
        if pipeline_cfg.vis:
            visualize_and_save(image, posenet_preds)
        # output_file = open(pipeline_cfg.output_binary_path, "wb")
        # pickle.dump([posenet_preds], output_file)
        # output_file.close()
        # to_csv(pipeline_cfg.output_binary_path, pipeline_cfg.output_csv_path)
        return posenet_preds


if __name__ == "__main__":
    main()