#!/usr/bin/env python
import numpy as np
import cv2
import rospy
import duckietown_utils as dtu

from cv_bridge import CvBridge
from duckietown_msgs.msg import BoolStamped, SegmentList
from sensor_msgs.msg import CompressedImage, Image

from merganzer_line_detector.utils import detections_to_image


class LineDetectorNode(object):
    def __init__(self):
        self.node_name = rospy.get_name()

        self.bridge = CvBridge()

        self.detector = None
        self.img_size = None
        self.top_cutoff = None
        self.verbose = False

        # Subscribers
        self.sub_image = rospy.Subscriber('~corrected_image/compressed',
                                          CompressedImage,
                                          self.process_image,
                                          queue_size=1)

        # Publishers
        self.pub_skeletons = None

        self.update_params(None)

        rospy.Timer(rospy.Duration.from_sec(2.), self.update_params)

    def loginfo(self, message):
        rospy.loginfo(message)

    def update_params(self, _event):
        self.verbose = rospy.get_param('~verbose', True)
        self.img_size = rospy.get_param('~img_size')
        self.top_cutoff = rospy.get_param('~top_cutoff')

        if self.detector is None:
            package_name, class_name = rospy.get_param('~detector')
            self.detector = dtu.instantiate_utils.instantiate(
                package_name, class_name)

        if self.verbose and (self.pub_skeletons is None):
            self.pub_skeletons = rospy.Publisher('~skeletons',
                                                 Image,
                                                 queue_size=1)

    def process_image(self, image_msg):
        # Decode the compressed image with OpenCV
        try:
            image_cv = dtu.bgr_from_jpg(image_msg.data)
        except ValueError as e:
            self.loginfo('Could not decode image: {0}'.format(e))
            return

        # Resize and crop the image
        height_original, width_original = image_cv.shape[:2]
        if ((height_original != self.img_size[0])
                or (width_original != self.img_size[1])):
            image_cv = cv2.resize(image_cv, (self.img_size[1], self.img_size[0]))

        image_cv = image_cv[self.top_cutoff:]

        skeletons = self.detector.detect_lines(image_cv)

        if self.verbose:
            skeletons_image = detections_to_image(skeletons)
            skeletons_msg = self.bridge.cv2_to_imgmsg(skeletons_image, 'bgr8')
            skeletons_msg.header.stamp = image_msg.header.stamp
            self.pub_skeletons.publish(skeletons_msg)

    def on_shutdown(self):
        self.loginfo('Shutdown...')


if __name__ == '__main__':
    rospy.init_node('merganzer_line_detector_node', anonymous=False)
    line_detector_node = LineDetectorNode()
    rospy.on_shutdown(line_detector_node.on_shutdown)
    rospy.spin()
