from abaqus import *
from abaqusConstants import *
mdb.models.changeKey(fromName='Model-1', toName='MasonryWallModel')
myModel = mdb.models['MasonryWallModel']
prop = myModel.ContactProperty('MortarDryFriction')
prop.CohesiveBehavior()

log = ""
try:
    prop.Damage(initTable=((200e3, 400e3, 400e3),), criterion=MAX_STRESS, useEvolution=ON, evolutionType=ENERGY, useMixedMode=ON, mixedModeType=TABULAR, evolTable=((10.0, 10.0, 10.0), ))
    log += "SUCCESS MIXED_MODE TABULAR\n"
except Exception as e:
    log += "ERR 1: " + str(e) + "\n"

try:
    prop.Damage(initTable=((200e3, 400e3, 400e3),), criterion=MAX_STRESS, useEvolution=ON, evolutionType=ENERGY, evolTable=((10.0, ), ))
    log += "SUCCESS SINGLE COLUMN\n"
except Exception as e:
    log += "ERR 2: " + str(e) + "\n"

with open('abaqus_damage_docs.txt', 'w') as out:
    out.write(log)
