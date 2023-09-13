#!/usr/bin/python3
import rospy
import os
from sensor_msgs.msg import CompressedImage, ImageMsg
from cv_bridge import CvBridge

import numpy as np
import models
import torch
import torch.nn.functional as F
from PIL import Image

mean = [0.485, 0.456, 0.406]
std = [0.229, 0.224, 0.225]

color_map = [(128, 64,128),
             (244, 35,232),
             ( 70, 70, 70),
             (102,102,156),
             (190,153,153),
             (153,153,153),
             (250,170, 30),
             (220,220,  0),
             (107,142, 35),
             (152,251,152),
             ( 70,130,180),
             (220, 20, 60),
             (255,  0,  0),
             (  0,  0,142),
             (  0,  0, 70),
             (  0, 60,100),
             (  0, 80,100),
             (  0,  0,230),
             (119, 11, 32)]

def input_transform(image):
    image = image.astype(np.float32)[:, :, ::-1]
    image = image / 255.0
    image -= mean
    image /= std
    return image


def load_pretrained(model, pretrained):
    pretrained_dict = torch.load(pretrained, map_location='cpu')
    if 'state_dict' in pretrained_dict:
        pretrained_dict = pretrained_dict['state_dict']
    model_dict = model.state_dict()
    pretrained_dict = {k[6:]: v for k, v in pretrained_dict.items() if (k[6:] in model_dict and v.shape == model_dict[k[6:]].shape)}
    msg = 'Loaded {} parameters!'.format(len(pretrained_dict))
    print('Attention!!!')
    print(msg)
    print('Over!!!')
    model_dict.update(pretrained_dict)
    model.load_state_dict(model_dict, strict = False)

    return model

class PIDNet:
    def __init__(self):
        self.node_name =  "PIDNet"
        rospy.init_node(self.node_name)

        image_sub = rospy.Subscriber('/grasscam/image_raw/compressed', CompressedImage, self.image_callback)
        self.pub = rospy.Publisher('/PIDNet', ImageMsg, queue_size=10)

    def image_callback(self, msg):
        # 画像データをROSメッセージから復元
        bridge = CvBridge()
        image = bridge.compressed_imgmsg_to_cv2(msg)

        img = image

        sv_img = np.zeros_like(img).astype(np.uint8)
        img = input_transform(img)
        img = img.transpose((2, 0, 1)).copy()
        img = torch.from_numpy(img).unsqueeze(0).cuda()
        pred = model(img)
        pred = F.interpolate(pred, size=img.size()[-2:],
                    mode='bilinear', align_corners=True)
        pred = torch.argmax(pred, dim=1).squeeze(0).cpu().numpy()
        for i, color in enumerate(color_map):
            for j in range(3):
                sv_img[:,:,j][pred==i] = color_map[i][j]
        sv_img = Image.fromarray(sv_img)

        # 推論結果をImage型に変換
        result_msg = bridge.cv2_to_imgmsg(infer_result[0].plot(), encoding="passthrough")


        # 推論結果をpublish
        self.pub.publish(result_msg)

if __name__=="__main__":
    PIDNet()
    rospy.spin()
