from random import random, choice, shuffle
import math
from functools import update_wrapper
try:
	import Image
	canImage = True
except:
	canImage = False
import logging
logLevel = logging.DEBUG
logging.basicConfig(level=logLevel)
def makeRandDist(nplays):
	if nplays == 0:
		return []
	rChance = 1.0 / nplays
	return [rChance] * nplays
def sigmoid(x):
	return .25 / (1 + (math.e ** (-1.0 * x)))
randDistributions = [makeRandDist(i) for i in range(100)]
#exampleSide = {'name':'town', 'canWinWith':[], 'players': []} #players will be filled in later
#examplePlayer = {'name':'1', 'side':'town', 'roles': [RoleBlocker], 'tempPowers':[],'powers':[],'willDie':False,'isSaved':False,'targetted': [],'actions':[]}

#exampleAction = {'targets': ['1','2'], 'actor': '3','hasGone': False,'action': RoleBlocker}

class InvestigationEffect(object):
	options = set(['ForceGuilty','ForceInnocent','CauseGuilty','CauseInnocent','NoEffect'])
	isGuiltyTable = {'ForceGuilty':True,'CauseGuilty':True,'CauseInnocent':False,'ForceInnocent':False,'NoEffect':False}
	@property
	def isGuilty(self):
		return self.level>0
	#rulesTable = {('ForceGuilty',('ForceInnocent',),True):'NoEffect',
	#		('ForceGuilty',('ForceInnocent',),False):'ForceGuilty',
	#		('ForceInnocent',('ForceGuilty',),True):'NoEffect',
	#		('ForceInnocent',('ForceGuilty',),False):'ForceInnocent',
	#		('CauseGuilty',('ForceInnocent',),True):'ForceInnocent',
	#		('CauseGuilty',('CauseInnocent',),True):'NoEffect',
	#		('CauseGuilty',('ForceInnocent','CauseInnocent'),False):'CauseGuilty',
	#		('CauseInnocent',('ForceInnocent','ForceGuilty','CauseGuilty'),False
#):'CauseInnocent',
	#		('NoEffect',('NoEffect',),True):'NoEffect'}
	#def buildRuleTable(self):
	#	self.rules =dict( ((x,{}) for x in self.options))
	#	for first,secondList,diff in self.rulesTable:
	#		secSet = set(secondList)
	#		if not diff:
	#			secSet = self.options.symmetric_difference(secSet)
	#		for rule in secSet:
	#			self.rules[first][rule] = self.rulesTable[(first,secondList,diff)]
	#			self.rules[rule][first] = self.rulesTable[(first,secondList,diff)]
	def __init__(self,guiltLevel):
		self.level = guiltLevel
	def __eq__(self,other):
		return self.level == other.level
	def __mul__(self,other):
		if abs(self.level)>abs(other.level):
			return InvestigationEffect(self.level)
		if abs(self.level)<abs(other.level):
			return InvestigationEffect(other.level)
		return InvestigationEffect(0)

NoEffect = InvestigationEffect(0)
CauseGuilty = InvestigationEffect(1)
CauseInnocent = InvestigationEffect(-1)
ForceGuilty = InvestigationEffect(2)
ForceInnocent = InvestigationEffect(-2)

class MafiaRole(object):
	name = "role"
	utilScore = 0.0
	resolveFirstOnTarget = False#if true, this action effects other actions and must be resolved before things may proceed 
	resolveFirstOnSelf = False
	isActive = False
	guilt = NoEffect
	def registerAction(self,action):
		action['hasGone'] = False
		action['action'] = self
		action['actor']['actions'].append(action)
		action['nominalTargets'] = action['targets'][:] #actual targets changes with being bus driven.  Nominal is who they think they're targetting
		for t in action['targets']:
			t['targetted'].append(action)
	def canAct(self,target,actor,action):
		for a in actor['targetted']:
			if a['action'].resolveFirstOnSelf and (action is not a) and not a['hasGone']:
				a['action'].doAction(a)
				return False
		for a in target['actions']:
			if a['action'].resolveFirstOnTarget and (action is not a) and not a['hasGone']:
				a['action'].doAction(a)
				return False
		return True
	def doAction(self,target, actor):
		"""Do the action, then remove it from the actor and target"""
		raise NotImplementedError, "Base class"
	def decision(self, players, owner, side,skill):
		raise NotImplementedError, "Base class"
	def selectTarget(self, players,owner,side,skill,utilityFunc,constraints=None):
		totalDist = getDistribution(players,owner,skill,utilityFunc)
		#constraints represent basic rules that aren't a matter of play, but rather basic understanding of the rules.
		#unlike normal utility functions, they apply after the random factor
		#in general, they ought to be an array where all members are 0 or 1
		if constraints:
			totalDist = normalizeList([d * constraints(p,owner) for d,p in zip(totalDist,players)])
		targetIndex= chooseOne(totalDist)
		return players[targetIndex]
class HarmfulRole(MafiaRole):
	utilScore = 5.0
	isActive = True
	def decision(self, players,owner,side,skill):
		#logging.debug("harmful action: %s.  side is: %s" % (repPlayer(owner),side['name']))
		target = self.selectTarget(players,owner,side,skill, harmfulUtility)
		#logging.debug("chose %s as target"%repPlayer(target))
		self.registerAction({'targets':[target],'actor':owner})
class HelpfulRole(MafiaRole):
	utilScore = 5.0
	isActive = False
	def decision(self,players,owner,side,skill):
		target = self.selectTarget(players,owner,side,skill,helpfulUtility)
		self.registerAction({'targets':[target],'actor':owner})
def chooseOne(options):
	rNum = random()
	count = 0
	sum=0.0
	for x in options:
		sum+=x
		if rNum<sum:
			return count
		count+=1
	return count-1#fuck it, let's just return the last element if it doesn't find one

def normalizeList(l):
	s = sum(l)
	if (s==0.0):
		logging.error(l)
	return [x / s for x in l]

def getDistribution(players, decider,skill, utilityFunc,invert=False):
		informed = normalizeList([utilityFunc(x,decider) for x in players])
		invSkill = 1-skill
		totalDist = [(skill * inf) + (invSkill * r) for inf,r in zip(informed,randDistributions[len(players)])]
		#logging.debug("%s %s produced distribution:\n%s"%(repPlayer(decider),utilityFunc.func_name,totalDist))
		if invert:
			totalDist = normalizeList([1.0/x for x in totalDist])
		return totalDist
		
def repPlayer(p):
	return "%s %s" % (p['name'],p['roles'][0].name)
def getNonTeam(player):
	return 20.0 + player['roleUtility'] + player['harmfulModifiers']
def isTeamMember(player,decider):
	return player['side']['name'] == decider['side']['name']
def isAlly(player,decider):
	return player['side'] in decider['side']['canWinWithNames']

def product(l,initial=1):
	return reduce( (lambda x,y: x*y), l, initial)

def utilityFunction(fn):
	class Utility(object):
		def __init__(self,fns):
			self.fns = fns
		def __call__(self,player,decider):
			return product([fun(player,decider) for fun in self.fns])
		def __mul__(self,util):
			return Utility(self.fns + util.fns)
	retval = update_wrapper(Utility([fn]),fn)
	return retval
@utilityFunction
def harmfulUtility(player,self):
	#print "utility of:",repPlayer(player),'to',repPlayer(self),player['side']==self['side'],
	score= 0.1 #base suspicion on everyone who isn't you
#	if (self['role'].name == 'mason'):
#		if player['name'] in  self['role'].masons:
#			score -= 4.0 #but masons are less suspicious
	#nonTeamScore = 20.0 + sum([x.utilScore for x in player['roles']]) + player['harmfulModifiers']
	#pside = player['side']['name']
	#if (pside != self['side']['name']):
	if not isTeamMember(player,self):
		nonTeamScore = getNonTeam(player)
		score+= nonTeamScore
#		if (player['role'].name is "godfather") and ("usurper" in [x['role'].name for x in player['side']['players']]):
#			score+= 5.0
		#if (pside not in self['side']['canWinWithNames']):
		if not isAlly(player,self):
			score+=10.0 * nonTeamScore
	#print score
	return score
@utilityFunction
def helpfulUtility(player,self):
	score = 5.0 #a baseline helpfulness
	friendlyScore = 20.0 + sum([x.utilScore for x in player['roles']]) + player['helpfulModifiers']
	#print friendlyScore, player['side']['name'], self['side']['name']
	if player['side']['name'] == self['side']['name']:
		score += 10.0 * friendlyScore
	if player['side']['name'] in [x['name'] for x in self['side']['canWinWith']]:
		score += friendlyScore
	return score

@utilityFunction
def neverTeam(player,self):
	if isTeamMember(player,self):
		return 0.0
	else:
		return 1.0

@utilityFunction
def neverSelf(player,self):
	if self['name'] == player['name']:
		return 0.0
	else:
		return 1.0

class RoleBlocker(HarmfulRole):
	name="roleblocker"
	utilScore = 10.0
	resolveFirstOnSelf = True
	def doAction(self,action):
		target = action['target'][0]
		actor = action['actor']
		if self.canAct(target,actor, action):
			for action in target['actions']:
				for target in action['targets']:
					target['targetted'].remove(action)
			target['actions'] = []
			action['hasGone'] = True
		
class BusDriver(MafiaRole):
	name="busdriver"
	utilscore = 7.0
	resolveFirstOnTarget = True
	isActive = True
	def decision(self,players, owner,side,skill):
		t1 = self.selectTarget(players,owner,side,skill,helpfulUtility)
		t2 = self.selectTarget(players,owner,side,skill, helpfulUtility)
		self.registerAction({'actor':owner,'targets':[t1,t2],'action':self})
	def doAction(self,action):
		target = action['targets']
		actor = action['actor']
		t1 = target[0]
		t2 = target[1]
		if (self.canAct(t1,actor,action) and self.canAct(t2,actor,action)): 
			logging.debug(''.join([repPlayer(actor)," bus drives ", repPlayer(t1)," with ", repPlayer(t2)]))
			temp = t1['targetted']
			t1['targetted'] = t2['targetted']
			t2['targetted'] = temp
			for a in t1['targetted']:
				if t1 in a['targets']:
					a['targets'][ a['targets'].index(t1) ] = t2
			for a in t2['targetted']:
				if t2 in a['targets']:
					a['targets'][ a['targets'].index(t2) ] = t1
			action['hasGone'] = True
		

class Doctor(MafiaRole):
	name="doctor"
	utilscore = 9.0
	isActive = True
	def doAction(self,action):
		if self.canAct(action['targets'][0],action['actor'],action):
			logging.debug(''.join([repPlayer(action['actor'])," protects ",repPlayer(action['targets'][0])]))
			if action['targets'][0]['name'] != action['actor']['name']:
				action['targets'][0]['willDie'] = False
				action['targets'][0]['isSaved'] = True
			action['hasGone'] = True
	def decision(self,players,owner,side,skill):
		distribution = getDistribution(players,owner,skill,helpfulUtility)
		atrisk = [i for i in range(len(players)) if (players[i]['willDie'] and ((players[i]['side']['name'] == owner['side']['name'])  or (players[i]['side']['name'] in [s['name'] for s in owner['side']['canWinWith']])))]
		for i in atrisk:
			distribution[i] += 100.0
		distribution = normalizeList(distribution)
		distribution = [d * neverSelf(p,owner) for d,p in zip(distribution,players)]
		target = players[chooseOne(distribution)]
		#print "doctor(",owner['name'],") saves:", repPlayer(target)
		self.registerAction({'targets':[target],'actor':owner})
class VT(MafiaRole):
	name = "vanilla townie"

class Goon(MafiaRole):
	guilt = CauseGuilty
	name = "goon"

class Godfather(MafiaRole):
	guilt = ForceInnocent

class Miller(MafiaRole):
	guilt = CauseGuilty
class Cop(HarmfulRole):
	name = "cop"
	utilscore = 10.0
	isActive = True
	def doAction(self,action):
		target = action['targets'][0]
		nomTarget = action['nominalTargets'][0]
		actor = action['actor']
		if self.canAct(target,actor,action):
			logging.debug(''.join([repPlayer(actor)," investigates ",repPlayer(target)," result: "]))
			if product([r.guilt for r in target['roles']],NoEffect).isGuilty:
				
			#if (target['side']['name'] != actor['side']['name']) and (target['side']['name'] not in [x['name'] for x in actor['side']['canWinWith']]):
				logging.debug("guilty")
				nomTarget['harmfulModifiers'] += 150.0
				actor['harmfulModifiers'] += 50.0
				actor['helpfulModifiers'] += 50.0
			else:
				logging.debug("innocent")
				nomTarget['helpfulModifiers'] += 3.0
		action['hasGone'] = True


class Kill(HarmfulRole):
	name = "kill"
	utilscore = 7.0
	def doAction(self,action):
		if self.canAct(action['targets'][0],action['actor'],action):
			logging.debug(''.join(["mafia attempts kill ", repPlayer(action['targets'][0])]))
			if not action['targets'][0]['isSaved']:
				logging.debug(''.join(["mafia kills ",repPlayer(action['targets'][0])]))
				action['targets'][0]['willDie'] = True
			action['hasGone'] = True
	def decision(self,players,owner,side,skill):
		target = self.selectTarget(players,owner,side,skill,harmfulUtility,constraints=neverTeam)
		self.registerAction({'targets':[target],'actor':owner})
		



def drawDiag(pixObj, start, size,color):
	end = min((size[0] - start[0]),size[1]-start[1])
	for i in range(end):
		pixObj[start[0]+i,start[1]+i] = color


class Game(object):
	players = []
	sides = []
	filename = None
	def __init__(self):
		if self.filename and canImage:
			self.canDraw = True
		else:
			self.canDraw = False
		self.basePlayers = self.players
		self.baseSides = self.sides
		self.buildLists()
	def buildLists(self):
		self.sides = [s.copy() for s in self.baseSides]
		self.players = []
		pcount = 0
		for s in self.sides:
			splayers = [{'name':str(i),'side':s['name'],'roles':[]} for i in range(pcount,pcount+s['number'])]
			powCount = 0
			for i in range(len(s['roles'])):
				splayers[i%len(splayers)]['roles']+=s['roles'][i]
			for p in splayers:
				if len(p['roles'])==0:
					if s['useScumSkill']:
						p['roles'] = [Goon]
					else:
						p['roles'] = [VT]
			self.players+=splayers
			pcount += s['number']
		for p in self.players:
			s = [x for x in self.sides if x['name'] == p['side']]
			if len(s)>0:
				p['side'] = s[0]
				if 'players' not in s[0]:
					s[0]['players'] = []
					s[0]['playerNames'] = []
				s[0]['players'].append(p)
				s[0]['playerNames'].append(p['name'])
			p['isSaved'] = False
			p['willDie'] = False
			p['actions'] = []
			p['targetted'] = []
			p['powers'] = []
			p['tempPowers'] = []
			p['roles'] = [x() for x in p['roles']]
			p['roleUtility'] = sum([x.utilScore for x in p['roles']])
		for s in self.sides:
			winWithList = []
			for ally in s['canWinWith']:
				w = [x for x in sides if x['name'] == ally]
				if (len(w)>0):
					winWithList.append(w[0])
			s['canWinWithNames'] = s['canWinWith']
			s['canWinWith'] = winWithList
			s['powers'] = [p() for p in s['powers']]
				
	def assignTeamPowers(self,side):
		tPows = [x for x in side['powers']]
		count = 0
		counts, players = zip(* sorted( [(len(x['roles']),x) for x in side['players']]))
		players = list(players)
		for pow in tPows:
			players[count%(len(players))]['tempPowers'].append(pow)
			count +=1
	def doNight(self,townSkill,scumSkill):
		skills = {False:townSkill, True:scumSkill}
		for player in self.players:
			player['powers'] = []
			player['tempPowers'] = []
			player['isSaved'] = False
		for side in self.sides:
			self.assignTeamPowers(side)
		for player in self.players:
			player['powers'] = player['tempPowers'] + [x for x in player['roles'] if x.isActive]
		for player in self.players:
			if len(player['powers'])>0:
				chosenAction = choice(player['powers'])
				chosenAction.decision(self.players,player,player['side'],skills[player['side']['useScumSkill']])
		actionsLeft = True
		actionOrder = self.players[:]
		shuffle(actionOrder)
		while True:
			succeeded = True
			alist = sum([ [x for x in player['actions'] if not x['hasGone']] for player in actionOrder], [])
			#print "action list is", [x['action'].name for x in alist]
			if len(alist) <= 0:
				break
			alist[0]['action'].doAction(alist[0])
		deadPlayers = [p for p in self.players if p['willDie']]
		for p in deadPlayers:
			self.players.remove(p)
			p['side']['players'].remove(p)
			if len(p['side']['players']) <= 0:
				self.sides.remove(p['side'])
		for player in self.players:
			player['targetted'] = []
			player['actions']=[]
	def doDay(self,townSkill,scumSkill):
		skills = {False:townSkill/1.2, True:scumSkill/1.2}
		#side_dists = [ s['name'] + ':' + str([p['name']+':'+p['side']['name']+':'+str(float(len(s)) * o) for o,p in zip(getDistribution(self.players,choice(s['players']),skill,harmfulUtility),self.players)]) for s in self.sides]
		#print side_dists
		s = self.sides[0]
		posDistrib = normalizeList([sum(x) for x in zip( * [ [skills[s['useScumSkill']] * float(len(s)) * o for o in getDistribution(self.players,choice(s['players']),skills[s['useScumSkill']],harmfulUtility)] for s in self.sides])])
		#print "town helpful utilities are:", [float(len(self.sides[1]['players'])) * o  for o in  getDistribution(self.players,choice(self.sides[1]['players']),townSkill,helpfulUtility,invert=True)]
		negDistrib = normalizeList([sum(x) for x in zip( * [ [(skills[s['useScumSkill']] *  float(len(s)) * o) for o in getDistribution(self.players,choice(s['players']),skills[s['useScumSkill']],helpfulUtility,invert=True)] for s in self.sides])])
		distribution = [product(x) for x in zip(*[posDistrib,negDistrib])]
		distribution = normalizeList(distribution)
		#print "distribution is"
		#print [p['name']+':'+p['side']['name']+':'+str(d) for d,p in zip(distribution,self.players)]
		lynchTarget = self.players[chooseOne(distribution)]
		self.players.remove(lynchTarget)
		lynchTarget['side']['players'].remove(lynchTarget)
		logging.debug("town lynches %s"%repPlayer(lynchTarget))
		if len(lynchTarget['side']['players']) <= 0:
			self.sides.remove(lynchTarget['side'])
	def isWinner(self,side):
		return all([(s in side['canWinWith']) or (s == side) for s in self.sides])
	def gameWon(self):
		#print [(s['name'], len(s['players'])) for s in self.sides]
		return all([self.isWinner(s) for s in self.sides])
	def runGame(self,townSkill, scumSkill):
		#print "scum skill:%f town skill:%f"%(townSkill, scumSkill)
		self.buildLists()
		for p in self.players:
			p['helpfulModifiers'] = 0.0
			p['harmfulModifiers'] = 0.0
		isWon = False
		day = 1
		while not isWon:
			multiplier = 0.75 + sigmoid(day - 3)
			skills = {False:townSkill * multiplier, True: scumSkill * multiplier}
			logging.debug("day %d town skill:%f scum skill:%f"%(day,skills[False],skills[True]))
			isWon = self.gameWon()
			if isWon:
				break
			self.doDay(townSkill,scumSkill)
			isWon = self.gameWon()
			if isWon:
				break
			self.doNight(townSkill,scumSkill)
			day+=1
		return self.sides
	def testGame(self,townSegments,scumSegments,gamesPerSegment,update=0,pixSize=1,filename=None,drawImage=True):
		gamesRan = 0
		updateOn = update-1
		self.canDraw = self.canDraw and drawImage
		sideNames = [s['name'] for s in self.sides]
		if self.canDraw:
			if filename:
				fName = filename
			else:
				fName = self.filename
			xSize = pixSize * townSegments
			ySize = pixSize * scumSegments
			imgs = []
			for s in self.sides:
				img = Image.new("RGBA",(pixSize * townSegments,pixSize * scumSegments),color=(0,0,0,255))
				img2 = Image.new("RGBA",(xSize,ySize),color=(255,255,255,255))
				imgPix = img.load()	
				imgPix2 = img2.load()
				imgs.append((s['name'],img,img2,imgPix,imgPix2))
		winTotals = dict( ( (s['name'],0) for s in self.sides) )
		deltaT = 1.0 / float(townSegments)
		deltaS = 1.0 / float(scumSegments)
		for x in range(townSegments):
			for y in range(scumSegments):
				segmentWins = dict([(s,0) for s in sideNames])
				for i in range(gamesPerSegment):
					winners = self.runGame(0.01 + float(x) * deltaT, 0.01 + float(y) * deltaS)
					for w in winners:
						winTotals[w['name']]+=1
						segmentWins[w['name']]+=1
					#townWins += 1 * any( (not w['useScumSkill'] for w in winners))
					gamesRan += 1
					if update and (gamesRan % update) == updateOn:
						print "Simulation has run",gamesRan,"games"
				if self.canDraw:
					for sName, img, img2,imgPix,imgPix2 in imgs:
						winDev = abs(segmentWins[sName] - (gamesPerSegment / 2))
						if winDev < (gamesPerSegment/4):#(gamesPerSegment/4):
						#print townWins, abs(townWins - (gamesPerSegment/2))
						#print x,y
							if winDev:
								color = 255
							else:
								color=175
							for i in range(pixSize):
								for j in range(pixSize):
									imgPix[i+(pixSize*x),j+(pixSize * y)] = (color,0,0,255)
					#elif abs(townWins - (gamesPerSegment/2)) < (gamesPerSegment/2):
					#	pixCol = (255 * abs(townWins - (gamesPerSegment/2))) / gamesPerSegment
					#	color=(pixCol,pixCol,pixCol)
						r = (255 * (gamesPerSegment - segmentWins[sName])) / gamesPerSegment
						g = (255 * segmentWins[sName]) / gamesPerSegment
						for i in range(pixSize):
							for j in range(pixSize):
								imgPix2[i+(pixSize*x),j+(pixSize * y)] = (r,g,0,255)
		if self.canDraw:
			for sName,img,img2,imgPix,imgPix2 in imgs:
				drawDiag(imgPix,(0,0),(xSize,ySize),(255,255,255,255))
				drawDiag(imgPix2,(0,0),(xSize,ySize),(0,0,0,255))
				for x in range(10,xSize,10):
					drawDiag(imgPix,(x,0),(xSize,ySize),(130,130,130,255))
					drawDiag(imgPix2,(x,0),(xSize,ySize),(30,30,30,255))
				for y in range(10,ySize,10):
					drawDiag(imgPix,(0,y),(xSize,ySize), (130,130,130,255))
					drawDiag(imgPix2,(0,y),(xSize,ySize), (30,30,30,255))
				img2.save(fName%(sName+"_distribution"))
				img.save(fName%(sName+"_contention"))
		return winTotals
		#print winTotals
	
		

class CMafia(Game):
	filename = "cmafia_%s.png"
	sides = [{'number':5,'roles':[[Doctor],[Cop]],'name':'town','powers':[],'canWinWith':[],'useScumSkill':False},
			{'number':2,'roles':[],'name':'mafia', 'powers':[Kill],'canWinWith':[],'useScumSkill':True}]

class ClassicSkMafia(Game):
	filename = "classicPlusSk_%s.png"
	sides = [{'number':5,'roles':[[Doctor],[Cop]],'name':'town','powers':[],'canWinWith':[],'useScumSkill':False},
			{'number':2,'roles':[],'name':'mafia', 'powers':[Kill],'canWinWith':[],'useScumSkill':True},
			{'number':1,'roles':[[Kill,Godfather]],'name':'sk','powers':[Kill],'canWinWith':[],'useScumSkill':True}]

class ClassicUnbalanced(Game):
	filename = "unbalanced_%s.png"
	sides = [{'number':5,'roles':[[Cop]],'name':'town','powers':[],'canWinWith':[],'useScumSkill':False},
			{'number':3,'roles':[],'name':'mafia', 'powers':[Kill],'canWinWith':[],'useScumSkill':True}]


class ClassicNoRoles(Game):
	filename = "cmafia_norole_%s.png"
	sides = [{'number':5,'roles':[],'name':'town','powers':[],'canWinWith':[],'useScumSkill':False},
			{'number':2,'roles':[],'name':'mafia', 'powers':[Kill],'canWinWith':[],'useScumSkill':True}]

class ClassicAllRoles(Game):
	filename = "cmafia_allrole_%s.png"
	sides = [{'number':5,'roles':[[Doctor],[Doctor],[BusDriver],[Cop],[Cop]],'name':'town','powers':[],'canWinWith':[],'useScumSkill':False},
			{'number':2,'roles':[],'name':'mafia', 'powers':[Kill],'canWinWith':[],'useScumSkill':True}]
	

class CMaf(Game):
	filename = "cmafia2_%s.png"
	sides = [{'number':8,'roles':[[Cop],[Doctor]]*2,'name':'town','powers':[],'canWinWith':[],'useScumSkill':False},
			{'number':3,'roles':[],'name':'mafia', 'powers':[Kill],'canWinWith':[],'useScumSkill':True}]
	

class CMaf2(Game):
	filename = "cmafia3_%s.png"
	sides = [{'number':8,'roles':[[Cop],[Doctor]]*1,'name':'town','powers':[],'canWinWith':[],'useScumSkill':False},
			{'number':5,'roles':[],'name':'mafia', 'powers':[Kill],'canWinWith':[],'useScumSkill':True}]
	
class BDMafia(Game):
	filename = "bdmaf_%s.png"
	sides = [{'number':8,'roles':[[Cop],[Doctor],[BusDriver]]*1,'name':'town','powers':[],'canWinWith':[],'useScumSkill':False},
			{'number':5,'roles':[],'name':'mafia', 'powers':[Kill],'canWinWith':[],'useScumSkill':True}]

#game = ClassicAllRoles()
#print game.testGame(100,100,20,update=7000)
#print [x['name'] for x in game.runGame(.75,.75)]
#winCount = {'mafia':0,'town':0}
#for i in range(200):
#	winner = game.runGame(.75,.25)[0]
#	winCount[winner['name']]+=1
#print winCount
