import os
import os.path as osp
import numpy as np
from rootnet_repo.common.utils.pose_utils import get_bbox
from pycocotools.coco import COCO
from rootnet_repo.main.config import cfg
import math

class MuCo:
    def __init__(self, data_split):
        self.data_split = data_split
        self.img_dir = osp.join('..', 'data', 'MuCo', 'data')
        self.train_annot_path = osp.join('..', 'data', 'MuCo', 'data', 'MuCo-3DHP.json')
        self.joint_num = 21
        self.joints_name = ('Head_top', 'Thorax', 'R_Shoulder', 'R_Elbow', 'R_Wrist', 'L_Shoulder', 'L_Elbow', 'L_Wrist', 'R_Hip', 'R_Knee', 'R_Ankle', 'L_Hip', 'L_Knee', 'L_Ankle', 'Pelvis', 'Spine', 'Head', 'R_Hand', 'L_Hand', 'R_Toe', 'L_Toe')
        self.min_depth = 1500
        self.max_depth = 7500
        self.joints_have_depth = True
        self.root_idx = self.joints_name.index('Pelvis')
        self.data = self.load_data()

    def load_data(self):

        if self.data_split == 'train':
            db = COCO(self.train_annot_path)
        else:
            print('Unknown data subset')
            assert 0

        data = []
        for iid in db.imgs.keys():
            img = db.imgs[iid]
            img_id = img["id"]
            img_width, img_height = img['width'], img['height']
            imgname = img['file_name']
            img_path = osp.join(self.img_dir, imgname)
            f = img["f"]
            c = img["c"]

            # crop the closest person to the camera
            ann_ids = db.getAnnIds(img_id)
            anns = db.loadAnns(ann_ids)
            
            # exclude too close persons
            root_depths = [ann['keypoints_cam'][self.root_idx][2] for ann in anns]
            closest_pid = root_depths.index(min(root_depths))
            pid_list = [closest_pid]
            for i in range(len(anns)):
                if i == closest_pid:
                    continue
                picked = True
                for j in range(len(anns)):
                    if i == j:
                        continue
                    dist = (np.array(anns[i]['keypoints_cam'][self.root_idx]) - np.array(anns[j]['keypoints_cam'][self.root_idx])) ** 2
                    dist_2d = math.sqrt(np.sum(dist[:2]))
                    dist_3d = math.sqrt(np.sum(dist))
                    if dist_2d < 500 or dist_3d < 500:
                        picked = False
                if picked:
                    pid_list.append(i)
            
            for pid in pid_list:
                joint_cam = np.array(anns[pid]['keypoints_cam'])
                root_cam = joint_cam[self.root_idx]

                if root_cam[2] < self.min_depth or root_cam[2] > self.max_depth:
                    continue
                
                joint_img = np.array(anns[pid]['keypoints_img'])
                joint_img = np.concatenate([joint_img, joint_cam[:,2:]],1)
                root_img = joint_img[self.root_idx]
                
                joint_vis = np.array(anns[pid]['keypoints_vis'])
                root_vis = joint_vis[self.root_idx,None]
                bbox = np.array(anns[pid]['bbox'])

                # sanitize bboxes
                x, y, w, h = bbox
                x1 = np.max((0, x))
                y1 = np.max((0, y))
                x2 = np.min((img_width - 1, x1 + np.max((0, w - 1))))
                y2 = np.min((img_height - 1, y1 + np.max((0, h - 1))))
                if w*h > 0 and x2 >= x1 and y2 >= y1:
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

                data.append({
                    'img_path': img_path,
                    'bbox': bbox,
                    'area': area,
                    'root_img': root_img, # [org_img_x, org_img_y, depth]
                    'root_cam': root_cam, # [X, Y, Z] in camera coordinate
                    'root_vis': root_vis,
                    'f': f,
                    'c': c
                })
        return data


