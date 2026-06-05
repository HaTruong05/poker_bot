#!/usr/bin/env python3
from __future__ import print_function

#import roslib
import sys
import numpy as np
import random
import math
import time
import os
import json
from poker_bot.poker import make_deck, best_hand, hand_str, card_str

import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from sensor_msgs.msg import Image
from nav_msgs.msg import Odometry
from geometry_msgs.msg import Twist, TwistStamped
from turtlebot3_msgs.srv import Sound as SoundSrv
from ament_index_python.packages import get_package_share_directory

import cv2
from cv_bridge import CvBridge, CvBridgeError
from ultralytics import YOLO


class image_converter(Node):


  	# instance variables
	def __init__(self):
		super().__init__('pokerBot')

		# Publishers
		self.image_pub = self.create_publisher(Image, "new_image", 10)
		self.cmd_vel_pub = self.create_publisher(TwistStamped, '/cmd_vel', 10)

		# Subscribers
		self.bridge = CvBridge()
		self.image_sub = self.create_subscription(Image,"image", self.image_callback, 10)
		self.odometrySubscription = self.create_subscription(Odometry, '/odom', self.odometryCallback, 10)
		self.client = self.create_client(SoundSrv, 'sound')
		
		# Tracks first phase, scanning for players by detecting faces. 
		self.scanningFaces = True
		
		# Tracks inbetween steps where TurtleBot stops to scan players' cards
		self.scanPlayerCards = False
		
		# Scan for community cards after registering every player and their hands
		self.scanCommunityCards = False
		self.communityCards = []

		# Tracks final phase of finding winner.
		self.findWinner = False
		self.players = {}

		# Tracks the player TurtleBot is currently facing
		self.curPlayer = None

		self.current_yaw = 0.0
		self.last_yaw = None
		self.accumulated_yaw = 0.0

		self.timer = self.create_timer(0.1, self.rotate)

		# card reg
		self.seenCards = []
		self.suit_map = {
			'C': '♣', 'D': '♦', 'H': '♥', 'S': '♠'
		}

		# use trained weights from github
		try:
			package_share = get_package_share_directory('card_recognition')
			model_path = os.path.join(package_share, 'models', 'poker_best.pt')
			self.cardModel = YOLO(model_path)

			cascade_path = os.path.join(package_share, 'models', 'haarcascade_frontalface_default.xml')
			self.face_cascade = cv2.CascadeClassifier(cascade_path)

			if self.face_cascade.empty():
				self.get_logger().error("CRITICAL: Failed to load Haar Cascade XML file!")
		except Exception as e:
			self.get_logger().error(f"weights not found: {e}")
			return

		# show what turtlebot see
		cv2.namedWindow("Pokerbot Vision", cv2.WINDOW_AUTOSIZE)

		self.get_logger().info("Card Detector Node successfully initialized")


	def image_callback(self, msg):
		try:
			cv_image = self.bridge.imgmsg_to_cv2(msg, 'bgr8')
			# cv_image = cv2.rotate(cv_image, cv2.ROTATE_180)
		except CvBridgeError as e:
			self.get_logger().error(f"CvBridge Error: {e}")
			return

		if cv_image is None:
			return

		# Face detection
		gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
		faces = self.face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=4, minSize=(30, 30))
		
		# put box around faces
		for (x, y, w, h) in faces:
			img = cv2.rectangle(cv_image, (x, y), (x+w, y+h), (0, 255, 0), 2)

		if self.scanningFaces and len(faces) > 0:
			is_new_player = True
			for p in self.players.values():
				saved_yaw = p['yaw']
				diff = self.current_yaw - saved_yaw
				diff = math.atan2(math.sin(diff), math.cos(diff))
				# If within 45 degrees of a saved player, consider it the same person
				if math.degrees(abs(diff)) < 45:
					is_new_player = False
					break

			if is_new_player: 
				newPlayer =  f'Player { len(self.players) + 1}'
				self.curPlayer = newPlayer

				self.players[newPlayer] = {
					"yaw": self.current_yaw, 
					"hand": [], 
					"hand score": 0,
					"hand name": ""
					}
				print(f"Found new player {newPlayer} at {math.degrees(self.current_yaw):.2f} degrees.")

				self.scanPlayerCards = True
				self.scanningFaces = False
				print(f"Stop to scanCommunityCards = False wait for {self.curPlayer} to show 2 cards")

		# Card detection
		h, w, _ = cv_image.shape
		if w != h:
			min_dim = min(h, w)
			start_x = (w - min_dim) // 2
			start_y = (h - min_dim) // 2
			processing_frame = cv_image[start_y:start_y+min_dim, start_x:start_x+min_dim]
		else:
			processing_frame = cv_image

		# Use the trained weights to get prediction of suit and rank
		results = self.cardModel(processing_frame, conf=0.8, verbose=False)

		for result in results:
			for box in result.boxes:
				class_id = int(box.cls[0])
				class_name = self.cardModel.names[class_id]

				if len(class_name) >= 2:
					rank = class_name[:-1]  # Everything up to the last character
					raw_suit = class_name[-1]   # The final character

					# map the notation to ours
					suit = self.suit_map.get(raw_suit, "Unknown")

					card_dict = {"rank": rank, "suit": suit}

				# add to the seen card list if new
				if rank != "Unknown" and suit != "Unknown" and card_dict not in self.seenCards:
					if self.scanPlayerCards:
						print(f"\nNew Card: {rank} of {suit}")
						self.seenCards.append(card_dict)

						playerData = self.players[self.curPlayer]

						if card_dict not in playerData['hand'] and len(playerData['hand']) < 2:
							playerData['hand'].append(card_dict)
							print(f"Assigned {card_str(card_dict)} to {self.curPlayer} ({len(playerData['hand'])}/2)")

						if len(playerData['hand']) == 2:
							print(f"{self.curPlayer} has their 2 cards. Resuming scan")
							self.scanPlayerCards = False
							self.scanningFaces = True

					elif self.scanCommunityCards:
						print(f"\nNew Card: {rank} of {suit}")
						self.seenCards.append(card_dict)

						if card_dict not in self.communityCards and len(self.communityCards) < 5:
							self.communityCards.append(card_dict)
							print(f"Added {card_str(card_dict)} to board ({len(self.communityCards)}/5)")

						if len(self.communityCards) == 5:
							print(f"All 5 community cards dealt: {hand_str(self.communityCards)}.\nCalculating winner.")
							self.scanCommunityCards = False
							
							# Calculate winner using community + player hands
							for player, playerData in self.players.items():
								comb = self.communityCards.copy()
								comb.extend(playerData['hand'])
								best_five, score, hand_name = best_hand(comb)
								playerData['hand score'] = score
								playerData['hand name'] = hand_name

								print(f"{player} has cards: {hand_str(playerData['hand'])}")
								print(f"{player} has a {hand_name} with {hand_str(best_five)}")
							
							# Trigger the final turn to face the winner
							self.findWinner = True

		# draw box around cards
		annotated_frame = results[0].plot()
		cv2.imshow("Pokerbot Vision", annotated_frame)
		cv2.waitKey(1)


	def rotate(self):
		"""Rotate to scan for players at the beginning and rotate to the winner at the end."""
		t0 = self.get_clock().now()

		out = TwistStamped()
		out.header.stamp = t0.to_msg()
		out.header.frame_id = "base_link"
		out.twist = Twist()

		if self.scanningFaces:
			out.twist.angular.z = -0.3  
		elif self.players and self.findWinner:
			winner = max(self.players, key=lambda i: self.players[i]["hand score"])
			target_yaw = self.players[winner]["yaw"]

			print(f"Winner is {winner} with {self.players[winner]['hand name']}")

			error = math.atan2(math.sin(target_yaw - self.current_yaw), math.cos(target_yaw - self.current_yaw))
			if abs(error) > 0.05:
				print(f"Turning to winner.")

				# Turn in the closest direction
				out.twist.angular.z = 0.3 if error > 0 else -0.3
			else:
				print(f"Game finished. Facing the winner.")
				out.twist.angular.z = 0.0
				self.findWinner = False

				self.cmd_vel_pub.publish(out)

				self.play_happy_sound(2)
				# 4. Trigger the second sound 1.5 seconds later
				self.sound_timer = self.create_timer(1.5, self.delayed_second_sound)
		else:
			out.twist.angular.z = 0.0

		# get new time
		t1 = self.get_clock().now()
		out.header.stamp = t1.to_msg()

		self.cmd_vel_pub.publish(out)


	def odometryCallback(self, data):
		orientation = data.pose.pose.orientation
		roll, pitch, yaw = euler_from_quaternion(orientation)
		self.current_yaw = yaw

		# Accumulate yaw to track 360-degree rotation
		if self.last_yaw is not None and self.scanningFaces:
			yaw_diff = yaw - self.last_yaw
			yaw_diff = math.atan2(math.sin(yaw_diff), math.cos(yaw_diff))
			self.accumulated_yaw += abs(yaw_diff)

			# Check if we have completed a full 360 degrees. 
			if self.accumulated_yaw >= 2 * math.pi:
				print("Scanning for players done. Now scanning for community cards.")
				self.scanningFaces = False
				self.scanCommunityCards = True

		self.last_yaw = yaw


	def play_happy_sound(self, value):
		print("Waiting for TurtleBot3 /sound service to become available...")

		if not self.client.wait_for_service(timeout_sec=1.0):
			print("ERROR: Sound service not found")
			return

		print(f"Service found! Playing happy beep value {value}...")

		req1 = SoundSrv.Request()
		req1.value = value

		self.client.call_async(req1)


	def delayed_second_sound(self):
		self.play_happy_sound(3)
		# Cancel the timer immediately so it doesn't loop
		self.sound_timer.cancel()


def euler_from_quaternion(quaternion):
		"""
		Converts quaternion (w in last place) to euler roll, pitch, yaw
		quaternion = [x, y, z, w], angular=geometry_msgs.msg.Vector3(x=0.0, y=0.0, z=-0.3))
		geometry_msgs.msg.Twist(linear=geometry_msgs.msg.Vector3(x=0.0, y=0.0, z=0.0)
		"""
		x = quaternion.x
		y = quaternion.y
		z = quaternion.z
		w = quaternion.w

		sinr_cosp = 2 * (w * x + y * z)
		cosr_cosp = 1 - 2 * (x * x + y * y)
		roll = np.arctan2(sinr_cosp, cosr_cosp)

		sinp = 2 * (w * y - z * x)
		pitch = np.arcsin(sinp)

		siny_cosp = 2 * (w * z + x * y)
		cosy_cosp = 1 - 2 * (y * y + z * z)
		yaw = np.arctan2(siny_cosp, cosy_cosp)

		return roll, pitch, yaw


def main(args=None):
	rclpy.init(args=args)
	ic = image_converter()
	rclpy.spin(ic)
	ic.destroy_node()
	cv2.destroyAllWindows()
	rclpy.shutdown()


if __name__ == '__main__':
	main(sys.argv)
