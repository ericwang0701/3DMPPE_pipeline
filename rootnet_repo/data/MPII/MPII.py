import os
import os.path as osp
import numpy as np
from pycocotools.coco import COCO
from rootnet_repo.main.config import cfg

class MPII:

    def __init__(self, data_split):
        self.data_split = data_split
        self.img_dir = osp.join('..', 'data', 'MPII')
        self.train_annot_path = osp.join('..', 'data', 'MPII', 'annotations', 'train.json')
        self.joint_num = 16
        self.joints_name = ('R_Ankle', 'R_Knee', 'R_Hip', 'L_Hip', 'L_Knee', 'L_Ankle', 'Pelvis', 'Thorax', 'Neck', 'Head', 'R_Wrist', 'R_Elbow', 'R_Shoulder', 'L_Shoulder', 'L_Elbow', 'L_Wrist')
        self.joints_have_depth = False
        self.root_idx = self.joints_name.index('Pelvis')
        self.min_depth = 0 # dummy value
        self.max_depth = 1 # dummy value
        self.data = self.load_data()

    def load_data(self):
        
        if self.data_split == 'train':
            db = COCO(self.train_annot_path)
        else:
            print('Unknown data subset')
            assert 0

        data = []
        for aid in db.anns.keys():
            ann = db.anns[aid]

            if (ann['image_id'] not in db.imgs) or ann['iscrowd'] or (ann['num_keypoints'] == 0):
                continue

            # sanitize bboxes
            x, y, w, h = ann['bbox']
            img = db.loadImgs(ann['image_id'])[0]
            width, height = img['width'], img['height']
            x1 = np.max((0, x))
            y1 = np.max((0, y))
            x2 = np.min((width - 1, x1 + np.max((0, w - 1))))
            y2 = np.min((height - 1, y1 + np.max((0, h - 1))))
            if ann['area'] > 0 and x2 >= x1 and y2 >= y1:
                bbox = np.array([x1, y1, x2-x1, y2-y1])
            else:
                continue

            # aspect ratio preserving bbox
            w = bbox[2]
            h = bbox[3]
            c_x = bbox[0] + w/2.
            c_y = bbox[1] + h/2.
            aspect_ratio = cfg.input_shape[1]/cfg.input_shape[0]
            if w > aspect_ratio * h:
                h = w / aspect_ratio
            elif w < aspect_ratio * h:
                w = h * aspect_ratio
            bbox[2] = w*1.25
            bbox[3] = h*1.25
            bbox[0] = c_x - bbox[2]/2.
            bbox[1] = c_y - bbox[3]/2.
            area = bbox[2]*bbox[3]

            # joints and vis
            joint_img = np.array(ann['keypoints']).reshape(self.joint_num,3)
            joint_vis = joint_img[:,2].copy().reshape(-1,1)
            joint_img[:,2] = 0
            root_img = joint_img[self.root_idx]
            root_vis = joint_vis[self.root_idx]

            imgname = db.imgs[ann['image_id']]['file_name']
            img_path = osp.join(self.img_dir, imgname)
            data.append({
                'img_path': img_path,
                'bbox': bbox,
                'area': area,
                'root_img': root_img, # [org_img_x, org_img_y, 0]
                'root_vis': root_vis,
                'f': np.array([1500, 1500]) # dummy value
            })

        return data
