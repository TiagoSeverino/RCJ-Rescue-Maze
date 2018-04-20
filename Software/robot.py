import time
import RPi.GPIO as GPIO
from arena.tiles import *

from sensor.led import *
from sensor.laser import *
from sensor.l298n.l298n import *
from sensor.cmps10.cmps10 import *
from sensor.switch import *
from sensor.tpa81.tpa81 import *
from sensor.kitDropper import *
from sensor.lineSensor import *

import pdb

class Robot():

	#Kit Dropper Pin
	KitDropperPin = 12

	#Line Sensor Pin
	LineSensorPin = 16

	#CMPS10 I2C Adress
	CMPS10_Addr = 0x61

	#TPA81 I2C Adress
	LeftThermometerAddr = 0x68
	RightThermometerAddr = 0x69

	#Pin1, Pin2, PWM
	motorLeft = [38, 40, 36] #Motor in Left
	motorRight = [26, 32, 24] #Motor in Right

	#Self Calibration
	BearOffSet = 0
	PitchOffSet = 0
	RollOffSet = 0

	#Vars
	TileSize = 30.0

	FrontGap = 0.3 #Margin For Robot To Stop in Center of Tile
	FrontDistance = 8.0
	AlignGap = 0.15

	MinTempGap = 5.0
	MinVictimTemp = 25.0

	ramp = False

	tile = 0

	def __init__(self):

		GPIO.setwarnings(False)
		GPIO.setmode(GPIO.BOARD)

		#Tilt Compensated Compass Setup
		self.compass = CMPS10(self.CMPS10_Addr)

		#Motors Setup
		self.MotorLeft = L298N(self.motorLeft[0], self.motorLeft[1], self.motorLeft[2])
		self.MotorRight = L298N(self.motorRight[0], self.motorRight[1], self.motorRight[2])

		#Lasers Setup
		self.Lasers = Lasers(7, 11, 13, 15, 19)

		#Kit Dropper Setup
		self.KitDropper = KitDropper(self.KitDropperPin)

		#Line Sensor Setup
		self.lineSensor = LineSensor(self.LineSensorPin)

		#Thermometer Setup
		self.thermometerLeft = TPA81(self.LeftThermometerAddr)
		self.thermometerRight = TPA81(self.RightThermometerAddr)

	"""
	### Functions
	"""

	def MoveTile(self, Ammount = 1, CheckVictims = False):
		(tile, distance) = self.GetTile(self.GetLaser(Laser.Front))

		finalTile = tile - Ammount

		if finalTile < 0:
			finalTile = 0

		gap = 0.4

		CheckVictimLeft = CheckVictims
		CheckVictimRight = CheckVictims

		while True:

			if CheckVictimLeft:
				if self.IsVictimLeft():
					CheckVictimLeft = False

			if CheckVictimRight:
				if self.IsVictimRight():
					CheckVictimRight = False

			(tile, distance) =  self.GetTile(self.GetLaser(Laser.Front))

			inclination = self.GetPitch()

			if (inclination > 10 and inclination < 50) or (inclination > 210 and inclination < 245):
				self.ramp = True
				finalTile = 0

			if tile > finalTile or (tile == finalTile and distance > self.FrontDistance + self.FrontGap):

				(frontLeftTile, frontLeftDist) = self.GetTile(self.GetLaser(Laser.FrontLeft))
				(frontRightTile, frontRightDist) = self.GetTile(self.GetLaser(Laser.FrontRight))

				if frontLeftDist > frontRightDist + gap:
					if self.ramp == False:
						self.Forward1(50, 60)
					else:
						self.Forward1(70, 85)
				elif frontLeftDist < frontRightDist - gap:
					if self.ramp == False:
						self.Forward1(60, 50)
					else:
						self.Forward1(85, 70)
				else:
					if self.ramp == False:
						self.Forward(3)
					else:
						self.Forward(5)

			elif tile < finalTile or (tile == finalTile and distance < self.FrontDistance - self.FrontGap):

				(backLeftTile, backLeftDist) = self.GetTile(self.GetLaser(Laser.BackLeft))
				(backRightTile, backRightDist) = self.GetTile(self.GetLaser(Laser.BackRight))

				if backLeftDist > backRightDist + gap:
					self.Backward1(25, 35)
				elif backLeftDist < backRightDist - gap:
					self.Backward1(35, 25)
				else:
					self.Backward(2)
			else:
				self.Break()
				time.sleep(0.1)
				self.AlignToWall()
				break

	def GetTile(self, distance):
		tile = 0

		while distance >= self.TileSize:
			tile += 1
			distance -= self.TileSize

		return (tile, distance)

	def RotateLeft(self):
		self.Left(5)
		time.sleep(0.55)
		self.Break()

		self.AlignToWall()

	def RotateRight(self):
		self.Right(5)
		time.sleep(0.55)
		self.Break()

		self.AlignToWall()

	def AlignToWall(self):

		speed = 1
		useLeft = False
		useRight = False

		(backLeft, frontLeft, frontRight, backRight) = (self.GetLaser(Laser.BackLeft), self.GetLaser(Laser.FrontLeft), self.GetLaser(Laser.FrontRight), self.GetLaser(Laser.BackRight))

		(backLeftTile, backLeftDist) = self.GetTile(backLeft)
		(frontLeftTile, frontLeftDist) = self.GetTile(frontLeft)

		(backRightTile, backRightDist) = self.GetTile(backRight)
		(frontRightTile, frontRightDist) = self.GetTile(frontRight)

		if frontLeftTile == backLeftTile:
			useLeft = True

		if frontRightTile == backRightTile:
			useRight = True

		if useLeft and useRight:
			if backLeftTile > backRightTile:
				useLeft = False
			elif backLeftTile < backRightTile:
				useRight = False

		while True:
			if useLeft == useRight:
				(backLeft, frontLeft, frontRight, backRight) = (self.GetLaser(Laser.BackLeft), self.GetLaser(Laser.FrontLeft), self.GetLaser(Laser.FrontRight), self.GetLaser(Laser.BackRight))

				(backLeftTile, backLeftDist) = self.GetTile(backLeft)
				(frontLeftTile, frontLeftDist) = self.GetTile(frontLeft)

				(backRightTile, backRightDist) = self.GetTile(backRight)
				(frontRightTile, frontRightDist) = self.GetTile(frontRight)
			elif useLeft:
				(backLeft, frontLeft) = (self.GetLaser(Laser.BackLeft), self.GetLaser(Laser.FrontLeft))

				(backLeftTile, backLeftDist) = self.GetTile(backLeft)
				(frontLeftTile, frontLeftDist) = self.GetTile(frontLeft)
			else:
				(frontRight, backRight) = (self.GetLaser(Laser.FrontRight), self.GetLaser(Laser.BackRight))

				(backRightTile, backRightDist) = self.GetTile(backRight)
				(frontRightTile, frontRightDist) = self.GetTile(frontRight)

			gap = self.AlignGap

			if useLeft:
				gap = self.AlignGap * (frontLeftTile + 1)
				if backLeftDist > frontLeftDist - gap and backLeftDist < frontLeftDist + gap:
					break

			if useRight:
				gap *= self.AlignGap * (frontRightTile + 1)
				if backRightDist > frontRightDist - gap and backRightDist < frontRightDist + gap:
					break

			if useLeft == useRight:
				if backLeftDist > frontLeftDist + gap and backRightDist < frontRightDist - gap:
					self.Right(speed)
				elif backLeftDist < frontLeftDist - gap and backRightDist > frontRightDist + gap:
					self.Left(speed)
				elif backLeftDist > frontLeftDist + gap and backRightDist > frontRightDist + gap:
					self.Forward(speed)
				else:
					self.Backward(speed)
			elif useLeft:
				if backLeftDist > frontLeftDist + gap:
					self.Right(speed)
				else: #elif backLeftDist < frontLeftDist - gap:
					self.Left(speed)
			else:
				if backRightDist < frontRightDist - gap:
					self.Right(speed)
				else: #elif backRightDist > frontRightDist + gap:
					self.Left(speed)

		self.Break()
		time.sleep(0.1)

	def GetWalls(self):
		(backLeft, frontLeft, front, frontRight, backRight) = self.GetAllLaser()

		wallLeft = False
		wallFront = False
		wallRight = False

		gap = self.TileSize

		if backLeft < gap or frontLeft < gap:
			wallLeft = True

		if front < gap:
			wallFront = True

		if backRight < gap or frontRight < gap:
			wallRight = True

		return (wallLeft, wallFront, wallRight)


	def DropKit(self, ammount=1):
		self.Break()
		time.sleep(0.1)
		self.KitDropper.drop(ammount)
		time.sleep(0.1)

	def IsVictimLeft(self):
		(ambLeft, objLeft) = self.GetTemperatureLeft()

		if ((objLeft - ambLeft) > self.MinTempGap) and objLeft > self.MinVictimTemp:
			self.RotateRight()
			self.DropKit()
			self.RotateLeft()
			print "Victim Detected"
			return True
		else:
			return False

	def IsVictimRight(self):
		(ambRight, objRight) = self.GetTemperatureRight()

		if ((objRight - ambRight) > self.MinTempGap) and objRight > self.MinVictimTemp:
			self.RotateLeft()
			self.DropKit()
			self.RotateRight()
			print "Victim Detected"
			return True
		else:
			return False

	"""
	### Sensors
	"""

	def GetAllLaser(self):
		return (self.GetLaser(Laser.BackLeft), self.GetLaser(Laser.FrontLeft), self.GetLaser(Laser.Front), self.GetLaser(Laser.FrontRight), self.GetLaser(Laser.BackRight))

	def GetLaser(self, laser = Laser.Front):
		distance = self.Lasers.getCM(laser)
		return distance

	def GetBear(self):
		bear = self.compass.bearing255()

		bear -= self.BearOffSet

 		if bear > 255:
 			bear -= 255
 		elif bear < 0:
 			bear += 255

  		return bear

	def GetPitch(self):
		pitch = self.compass.pitch()

		pitch -= self.PitchOffSet

 		if pitch > 255:
 			pitch -= 255
 		elif pitch < 0:
 			pitch += 255

  		return pitch

	def GetRoll(self):
		roll = self.compass.roll()

		roll -= self.RollOffSet

 		if roll > 255:
 			roll -= 255
 		elif roll < 0:
 			roll += 255

  		return roll

	def GetTemperatureLeft(self):
		self.ambTempLeft = self.thermometerLeft.ambientTemperature()
		self.objTempLeft = self.thermometerLeft.highestTemp()

		return (self.ambTempLeft, self.objTempLeft)


	def GetTemperatureRight(self):
		self.ambTempRight = self.thermometerRight.ambientTemperature()
		self.objTempRight = self.thermometerRight.highestTemp()

		return (self.ambTempRight, self.objTempRight)

	def GetTileType(self):
		if self.lineSensor.IsBlackTile():
			return TileType.Black
		else:
			return TileType.White

	"""
	### Motor Control ###
	"""

	def MotorSpeedCalibration(self, speed):
		mLeft = 0
		mRight = 0

		if speed == 1:
			mLeft = 15
			mRight = 15
		elif speed == 2:
			mLeft = 40
			mRight = 40
		elif speed == 3:
			mLeft = 60
			mRight = 60
		elif speed == 4:
			mLeft = 80
			mRight = 80
		elif speed == 5:
			mLeft = 100
			mRight = 100

		return (mLeft, mRight)

	def Forward(self, speed = 3):
		(speedLeft, speedRight) = self.MotorSpeedCalibration(speed)
		self.MotorLeft.Forward(speedLeft)
		self.MotorRight.Forward(speedRight)

	def Forward1(self, speedLeft, speedRight):
		self.MotorLeft.Forward(speedLeft)
		self.MotorRight.Forward(speedRight)

	def Backward(self, speed = 2):
		(speedLeft, speedRight) = self.MotorSpeedCalibration(speed)
		self.MotorLeft.Backward(speedLeft)
		self.MotorRight.Backward(speedRight)

	def Backward1(self, speedLeft, speedRight):
		self.MotorLeft.Backward(speedLeft)
		self.MotorRight.Backward(speedRight)


	def Left(self, speed = 4):
		(speedLeft, speedRight) = self.MotorSpeedCalibration(speed)
		self.MotorLeft.Backward(speedLeft)
		self.MotorRight.Forward(speedRight)


	def Right(self, speed = 4):
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
