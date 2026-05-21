#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from nav_msgs.msg import Odometry
from geometry_msgs.msg import TransformStamped, Vector3
from tf2_ros import TransformBroadcaster

class OdomToTF(Node):
    def __init__(self):
        super().__init__('odom_to_tf')
        self.broadcaster = TransformBroadcaster(self)
        
        # Uso corretto dei parametri
        self.declare_parameter('odom_topic', '/odom')
        self.declare_parameter('child_frame', 'body_link')
        
        # Estraiamo la stringa dal parametro
        odom_topic = self.get_parameter('odom_topic').get_parameter_value().string_value
        self.child_frame_id = self.get_parameter('child_frame').get_parameter_value().string_value

        self.subscription = self.create_subscription(
            Odometry,
            odom_topic, # Ora questa è una stringa valida
            self.odom_callback,
            10)
        
        self.get_logger().info(f"Nodo avviato. Child frame: {self.child_frame_id}")

    def odom_callback(self, msg):
        t = TransformStamped()
        t.header.stamp = msg.header.stamp
        t.header.frame_id = msg.header.frame_id 
        t.child_frame_id = self.child_frame_id 
        
        t.transform.translation = Vector3(x=msg.pose.pose.position.x, 
                                          y=msg.pose.pose.position.y, 
                                          z=msg.pose.pose.position.z)
        t.transform.rotation = msg.pose.pose.orientation

        self.broadcaster.sendTransform(t)

def main(args=None):
    rclpy.init(args=args)
    node = OdomToTF()
    rclpy.spin(node)
    rclpy.shutdown()

if __name__ == '__main__':
    main()