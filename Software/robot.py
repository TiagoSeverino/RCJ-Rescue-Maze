import time
import RPi.GPIO as GPIO
from arena.tiles import *

from sensor.l298n import L298N
from sensor.srf04 import SRF04
from sensor.cmps03 import CMPS03
from sensor.cmps10 import CMPS10

class Robot():

	#CMPS03
	CMPS03_Addr = 0x60

	#CMPS10
	CMPS10_Addr = 0x61

	#MLX90614
	LeftThermometerAddr = 0x5a
	RightThermometerAddr = 0x2a

	#SRF04
	LeftSonarTRIG = 19
	LeftSonarECHO = 11

	FrontSonarTRIG = 21
	FrontSonarECHO = 13

	RightSonarTRIG = 23
	RightSonarECHO = 15


	#Pin1, Pin2, PWM
	motorLeft = [37, 35, 33] #Motor in Left
	motorRight = [40, 38, 36] #Motor in Right

	#Vars
	TileSize = 30.0
	Direction = 0 # Compass Direction: 0, North; 1, East; 2, South; 3, West

	def __init__(self):

		GPIO.setwarnings(False)
		GPIO.setmode(GPIO.BOARD)

		#Compass Setup
		self.compass = CMPS03(self.CMPS03_Addr)

		#Tilt Compensated Compass Setup
		self.tiltCompass = CMPS10(self.CMPS10_Addr)

		#Sonar Setup
		self.sonar = []
		
		self.sonar.append(SRF04(self.LeftSonarTRIG, self.LeftSonarECHO))
		self.sonar.append(SRF04(self.FrontSonarTRIG, self.FrontSonarECHO)) 
		self.sonar.append(SRF04(self.RightSonarTRIG, self.RightSonarECHO))

		#Motors Setup
		self.MotorLeft = L298N(self.motorLeft[0], self.motorLeft[1], self.motorLeft[2])
		self.MotorRight = L298N(self.motorRight[0], self.motorRight[1], self.motorRight[2])

		#Register Position
		self.CompassOffset = self.compass.bearing255()

	"""
	### Functions
	"""

	def MoveTile(self):
		(tile, distance) = self.GetTile(self.GetSonar())

		if tile > 0:
			finalTile = tile - 1
		else:
			finalTile = 0

		positionGap = 0.5 #Margin For Robot To Stop in Center of Tile
		frontDistance = (self.TileSize / 2) - 7.5

		while True:

			(tile, distance) = self.GetTile(self.GetSonar())

			if tile > finalTile:
				tileLeft, distanceLeft = self.GetTile(self.GetSonar("left"))
				tileRight, distanceRight = self.GetTile(self.GetSonar("right"))

				if tileLeft > tileRight:
					self.Forward2(60, 80)
				else:
					self.Forward2(80, 60)
			elif tile < finalTile:
				self.Backward()
			else:
				if distance < frontDistance - positionGap:
					self.Backward()
				elif distance > frontDistance + positionGap:
					self.Forward()
				else:
					self.Break()
					
					time.sleep(0.5)

					self.Rotate(self.Direction)

					break

		if tile == 0:
			return False
		else:
			return True

	def GetTile(self, distance):
		tile = 0

		while distance >= self.TileSize:
			tile += 1
			distance -= self.TileSize

		return (tile, distance)

	def RotateLeft(self):
		self.Left(5)
		time.sleep(3)

	def RotateRight(self):
		self.Right(5)
		time.sleep(3)

	def RotateLeft1(self):

		if self.Direction == Direction.Up:
			self.Rotate(Direction.Left)
		elif self.Direction == Direction.Right:
			self.Rotate(Direction.Up)
		elif self.Direction == Direction.Bottom:
			self.Rotate(Direction.Right)
		elif self.Direction == Direction.Left:
			self.Rotate(Direction.Bottom)

	def RotateRight1(self):
		
		if self.Direction == Direction.Up:
			self.Rotate(Direction.Right)
		elif self.Direction == Direction.Right:
			self.Rotate(Direction.Bottom)
		elif self.Direction == Direction.Bottom:
			self.Rotate(Direction.Left)
		elif self.Direction == Direction.Left:
			self.Rotate(Direction.Up)

	def Rotate(self, position, loop = True, margin = 2):

		rotateSpeed = 3

		while True:
			
			direction = self.GetBearing()
			

			if position == Direction.Up:
				if direction < 255.0 - margin and direction >= 180.0:
					self.Right(speed = rotateSpeed)
				elif direction > 0.0 + margin and direction <= 180.0:
					self.Left(speed = rotateSpeed)
				else:
					self.Direction = Direction.Up
					break
			elif position == Direction.Right:
				if direction < 64.0 - margin or direction >= 270.0:
					self.Right(speed = rotateSpeed)
				elif direction > 64.0 + margin and direction <= 270.0:
					self.Left(speed = rotateSpeed)
				else:
					self.Direction = Direction.Right
					break
			elif position == Direction.Bottom:
				if direction < 127.0 - margin:
					self.Right(speed = rotateSpeed)
				elif direction > 127.0 + margin:
					self.Left(speed = rotateSpeed)
				else:
					self.Direction = Direction.Bottom
					break
			else:
				if direction < 191.0 - margin and direction >= 90.0:
					self.Right(speed = rotateSpeed)
				elif direction > 191.0 + margin or direction <= 90.0:
					self.Left(speed = rotateSpeed)
				else:
					self.Direction = Direction.Left
					break
			
			if loop == False:
				break

		self.Break()
		time.sleep(0.5)

	def GetWalls(self):
		sonarLeft = self.GetSonar("Left")
		sonarFront = self.GetSonar("Front")
		sonarRight = self.GetSonar("Right")

		wallLeft = True
		wallFront = True
		wallRight = True

		gap = self.TileSize/6 * 5

		if sonarLeft > gap:
			wallLeft = False

		if sonarFront > gap:
			wallFront = False

		if sonarRight > gap:
			wallRight = False

		return (wallLeft, wallFront, wallRight)


	"""
	### Sensors
	"""

	def GetBearing(self):
		bearing = self.compass.bearing255()

		bearing -= self.CompassOffset

		if bearing > 255.0:
			bearing -= 255.0
		elif bearing < 0.0:
			bearing += 255.0

		return bearing

	def GetSonar(self, direction = "Front"):

		direction = direction.lower()
		sonarNumber = 0

		if direction == "left":
			sonarNumber = 0
		elif direction == "right":
			sonarNumber = 2
		else: # Front Sonar
			sonarNumber = 1

		distance = self.sonar[sonarNumber].getCM()

		return distance

	"""
	### Motor Control ###
	"""

	def MotorSpeedCalibration(self, speed):
		mLeft = 0
		mRight = 0

		if speed == 1:
			mLeft = 19
			mRight = 20
		elif speed == 2:
			mLeft = 35
			mRight = 40
		elif speed == 3:
			mLeft = 50
			mRight = 60
		elif speed == 4:
			mLeft = 65
			mRight = 80
		elif speed == 5:
			mLeft = 80
			mRight = 100

		return (mLeft, mRight)

	def Forward(self, speed = 2):
		(speedLeft, speedRight) = self.MotorSpeedCalibration(speed)
		self.MotorLeft.Forward(speedLeft)
		self.MotorRight.Forward(speedRight)

	def Forward2(self, speedLeft, speedRight):
		self.MotorLeft.Forward(speedLeft)
		self.MotorRight.Forward(speedRight)

	def Backward(self, speed = 2):
		(speedLeft, speedRight) = self.MotorSpeedCalibration(speed)
		self.MotorLeft.Backward(speedLeft)
		self.MotorRight.Backward(speedRight)


	def Left(self, speed = 2):
		(speedLeft, speedRight) = self.MotorSpeedCalibration(speed)
		self.MotorLeft.Backward(speedLeft)
		self.MotorRight.Forward(speedRight)


	def Right(self, speed = 2):
		(speedLeft, speedRight) = self.MotorSpeedCalibration(speed)
		self.MotorLeft.Forward(speedLeft)
		self.MotorRight.Backward(speedRight)


	def Stop(self, speed = 0):
		(speedLeft, speedRight) = self.MotorSpeedCalibration(speed)
		self.MotorLeft.Stop(speedLeft)
		self.MotorRight.Stop(speedRight)


	def Break(self, speed = 5):
		(speedLeft, speedRight) = self.MotorSpeedCalibration(speed)
		self.MotorLeft.Break(speedLeft)
		self.MotorRight.Break(speedRight)


	def Exit(self):
		GPIO.cleanup()