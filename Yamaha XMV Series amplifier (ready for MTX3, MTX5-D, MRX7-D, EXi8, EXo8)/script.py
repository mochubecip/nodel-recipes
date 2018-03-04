'''XMV Series (ready for MTX3, MTX5-D, MRX7-D, EXi8, EXo8), see script for manual location.'''

# taken from (the large) manual:
# http://download.yamaha.com/api/asset/file/?language=en&site=countrysite-master.prod.wsys.yamaha.com&asset_id=63959

# TODO:
# - turn a few of the static addresses and counts into parameters

DEFAULT_TCPPORT = 49280

param_Disabled = Parameter({'schema': {'type': 'boolean'}})
param_IPAddress = Parameter({'title': 'IP address', 'schema': {'type': 'string'}})

DEFAULT_NUMCHANNELS = 8
param_NumChannels = Parameter({'title': 'Channels', 'desc': 'Number of channels', 'schema': {'type': 'integer', 'hint': DEFAULT_NUMCHANNELS}})

local_event_DisableMeters = LocalEvent({'group': 'Meters', 'schema': {'type': 'boolean'}})

INPUT_METER_ADDR  = 'MTX:mtr_512/20000/meter'
OUTPUT_METER_ADDR = 'MTX:mtr_512/20001/meter'

inputMeterSignals = list()
outputMeterSignals = list()

# create input and output channel meters

for i in range(16):
  signal = Event('Input %s Meter' % (i+1), {'title': '#%s' % (i+1), 'group': 'Input Meters', 'order': 8000+next_seq(), 'schema': {'type': 'integer'}})
  inputMeterSignals.append(signal)
  
for i in range(8):
  signal = Event('Output %s Meter' % (i+1), {'title': '#%s' % (i+1), 'group': 'Output Meters', 'order': 8000+next_seq(), 'schema': {'type': 'integer'}})
  outputMeterSignals.append(signal)
  
# parameters
INT_SCHEMA = {'type': 'integer'}
INT_CONVERTERS = [ lambda arg: int(arg),   # first converter is converting raw string value from device
                   lambda arg: str(arg) ]  # second is converting nodel type to raw string device

STRING_CONVERTERS = [ lambda arg: arg,     # this does NO conversation obviously
                      lambda arg: arg ] 

MUTE_SCHEMA = {'type': 'string', 'enum': ['On', 'Off']}
MUTE_CONVERTERS = [ lambda arg: 'On' if arg == '1' else 'Off', 
                    lambda arg: 1 if arg == 'On' else 0 ]

POLARITY_SCHEMA = {'type': 'string', 'enum': ['Normal', 'Inverse']}
POLARITY_CONVERTERS = [ lambda arg: 'Inverse' if arg == '1' else 'Normal', 
                        lambda arg: 1 if arg == 'Inverse' else 0 ]

POWER_SCHEMA = {'type': 'string', 'enum': ['On', 'Off']}
POWER_CONVERTERS = [ lambda arg: 'Off' if arg == '1' else 'On', # yes, 1 means Off / stand-by
                     lambda arg: 1 if arg == 'Off' else 0 ]

INPUTSEL_LOOKUP = [('0', 'Analog'), ('1', 'Digital'), ('2', 'Multiple')]
INPUTSEL_SCHEMA = {'type': 'string', 'enum': [y for x, y in INPUTSEL_LOOKUP]}
INPUTSEL_byCode = dict([(x, y) for x, y in INPUTSEL_LOOKUP])
INPUTSEL_byName = dict([(y, x) for x, y in INPUTSEL_LOOKUP])
INPUTSEL_CONVERTERS = [ lambda arg: INPUTSEL_byCode[arg],
                        lambda arg: INPUTSEL_byName[arg] ]

SENSI_SCHEMA = {'type': 'string', 'enum': ['-20dBFS', '-3dBFS']}
SENSI_CONVERTERS = [ lambda arg: '-3dBFS' if arg == '1' else '-20dBFS',
                     lambda arg: 1 if arg == '-3dBFS' else 0 ]

CHSEL_SCHEMA = {'type': 'string', 'enum': ['-20dBFS', '-3dBFS']}
CHSEL_CONVERTERS = [ lambda arg: 'Digital' if arg == '1' else 'Analog',
                     lambda arg: 1 if arg == 'Digital' else 0 ]


PARAMETERS = [
  #     0:address                 1:group        2:name               3:schema         4:converters
      ['MTX:mem_512/1/6/0/0/0/0', "Power",       "Power",             POWER_SCHEMA,    POWER_CONVERTERS],
      ['MTX:mem_512/1/6/0/0/0/0', "Utility",     "Input Select",      INPUTSEL_SCHEMA, INPUTSEL_CONVERTERS],
      ['MTX:mem_512/1/6/0/0/0/0', "Sensitivity", "Input Sensitivity", SENSI_SCHEMA,    SENSI_CONVERTERS]
  ]  

@after_main
def channelsConfig():
  NUM_CHANNELS = param_NumChannels or DEFAULT_NUMCHANNELS
  for i in range(NUM_CHANNELS):
    PARAMETERS.extend([
      ['MTX:mem_512/1/4/%s/0/0/0' % i,  "Attenuation (Signal Processing)",         "Channel %s Att" % (i+1),          INT_SCHEMA,      INT_CONVERTERS],
      ['MTX:mem_512/1/4/%s/0/1/0' % i,  "Digital Attenuation (Signal Processing)", "Channel %s Digital Att" % (i+1),  INT_SCHEMA,      INT_CONVERTERS],
      ['MTX:mem_512/1/4/%s/0/2/0' % i,  "Muting",                                  "Channel %s Mute" % (i+1),         MUTE_SCHEMA,     MUTE_CONVERTERS],
      ['MTX:mem_512/1/4/%s/0/3/0' % i,  "Polarity",                                "Channel %s Polarity" % (i+1),     POLARITY_SCHEMA, POLARITY_CONVERTERS],
        
      # Not sure but this doesn't seem to be working: (see page 107)
      # ['MTX:mem_512/1/11/%s/0/0/0' % i, "Channel Utility",   "Channel %s Input Select" % (i+1), CHSEL_SCHEMA,    CHSEL_CONVERTERS],
    ])

    
# for async feedback

signalsByAddr = {}      # e.g. { 'MTX:mem_512/1/4/0/0/1/0': (`convertor`, `a signal`) }
signalsByDevStatus = {} # e.g. { 'lockstatus': (`convertor`, `a signal`) }

# <main ---

@after_main
def bindAllParameters():
  for paramInfo in PARAMETERS:
    bindParameters(paramInfo)

def bindParameters(paramInfo):
  address = paramInfo[0] # e.g. 'MTX:mem_512/1/4/0/0/1/0'
  group = paramInfo[1]
  name = paramInfo[2]
  schema = paramInfo[3]
  converters = paramInfo[4]
  
  log(2, 'binding address:%s group:%s name:%s schema:%s' % (address, group, name, schema))
  
  # signal
  signal = Event(name, {'order': next_seq(), 'group': group, 'schema': schema})
  
  # getter
  getter = Action('Get ' + name, lambda arg: getParam(address, option=5, converter=converters[0], signal=signal),
                  {'group': group, 'order': next_seq()})
  
  # setter
  setter = Action(name, lambda arg: setParam(address, arg, option=5, converters=converters, signal=signal),
                  {'group': group, 'order': next_seq(), 'schema': schema})
  
  # for async feedback from device e.g. [NOTIFY set MTX:mem_512/1/4/0/0/1/0 0 0 -75 "-75"]
  signalsByAddr[address] = (converters[0], signal)
  
  # kick-off a getter within the next 15 seconds and then every 2 minutes or so
  Timer(lambda: getter.call(), random(120,150), random(10,15))
  
  
def main():
  if param_Disabled:
    console.warn('Disabled! nothing to do')
    return
  
  if is_blank(param_IPAddress):
    console.warn('No IP address set; nothing to do')
    return
  
  dest = '%s:%s' % (param_IPAddress, DEFAULT_TCPPORT)
  
  console.info('Will connect to [%s]' % dest)
  tcp.setDest(dest)

def kickOffMeters():
  # do nothing if meters are disabled
  if local_event_DisableMeters.getArg():
    return
  
  lookup_local_action('meterStart').call({'address': INPUT_METER_ADDR,  'interval': 333})
  lookup_local_action('meterStart').call({'address': OUTPUT_METER_ADDR, 'interval': 333})
  
# give it 15 seconds before getting the meters and repeat request every X seconds
# since they automatically stop after a period of time
Timer(kickOffMeters, 8, 15)

# --- main>
  
# <protocol ---

NOTIFY = "NOTIFY"
OK = "OK"
ERROR = "ERROR"
METER = "METER"

# (see splitIntoOptions function at bottom)

def handleNotifyMtr(options):
  # e.g. meter: 
  # NOTIFY mtr MTX:mtr_512/20000/meter level 1b 1c 1c 1c 1b 1d 1d 1c 00 00 00 00 00 00 00 00
  option3 = options[2]
  
  if option3 == INPUT_METER_ADDR:
    metersSignals = inputMeterSignals
    
  elif option3 == OUTPUT_METER_ADDR:
    metersSignals = outputMeterSignals
    
  offset = 0
  for levelCode in options[4:]:
    # see page 58
    metersSignals[offset].emitIfDifferent(-126 + int(levelCode, 16))
    offset += 1

def parseResp(resp, option=-1, converter=None, signal=None):
  # Example responses:
  #
  #   OK devstatus fs "44.1kHz"
  #   ERROR devstatus InvalidArgument
  options = splitIntoOptions(resp)
  
  option0 = options[0]
  
  if option0 == ERROR:
    console.warn('Got bad response [%s]' % resp)
  
  # otherwise pass through 'OK' and 'NOTIFY'
  if option0 == OK or option0 == NOTIFY:
    option1 = options[1]
    
    if option1 == 'mtr':
      # this is considered stray feedback - should very rarely, if ever get here, but 
      # have seen that the amp doesn't/cannot guarentee no cross-talk between call requests and 
      # async notify events.
      
      # just pass it through to the meter handler
      handleNotifyMtr(options)
    
    if option >= 0:
      if converter == None:
        signal.emit(options[option])
      
      else:
        try:
          signal.emit(converter(options[option]))
        except:
          console.warn('conversion failure dealing with: [%s]' % options)
          
    
def getParameter(memNum, uniqueID, elemNum, xPos, yPos, paramNum, indexNum, option=-1, signal=None):
  tcp.request('get MTX:mem_%s/%s/%s/%s/%s/%s/%s 0 0' % (memNum, uniqueID, elemNum, xPos, yPos, paramNum, indexNum), 
              lambda resp: parseResp(resp, option, signal))
  
def getParam(addr, option=-1, converter=None, signal=None):
  tcp.request('get %s 0 0' % (addr), 
              lambda resp: parseResp(resp, option, converter, signal))
  
def setParam(addr, arg, option=-1, converters=None, signal=None):
  tcp.request('set %s 0 0 %s' % (addr, converters[1](arg)), 
              lambda resp: parseResp(resp, option, converters[0], signal))

  
# special commands (non-generic parameters)
 
#         --- device Status ---

def bindDevStatusCommand(name, group, cmd):
  signal = Event(name, {'group': group, 'order': next_seq(), 'schema': {'type': 'string'}})
  
  def handler(arg):
    tcp.request('devstatus ' + cmd, lambda resp: parseResp(resp, option=3, signal=signal))
    
  action = Action('Get %s' % name, handler, {'group': group, 'order': next_seq()})
  
  # for async feedback via notify
  signalsByDevStatus[cmd] = (STRING_CONVERTERS[0], signal)
  
  # kick-off more frequest timers
  Timer(lambda: action.call(), random(60,90), random(5,10))
  
@after_main
def bindDevStatuses():
  group = 'Device Status'
  bindDevStatusCommand('Device Run Mode', group, 'runmode')  
  bindDevStatusCommand('Device Error Status', group, 'error')
  bindDevStatusCommand('Device Sampling Freq', group, 'fs')
  bindDevStatusCommand('Device Work Clock Status', group, 'lockstatus')  
  
  
#         --- product info ---

def bindDevInfoCommand(name, group, cmd):
  signal = Event(name, {'group': group, 'order': next_seq(), 'schema': {'type': 'string'}})
  
  def handler(arg):
    tcp.request(cmd, lambda resp: parseResp(resp, option=3, signal=signal))
    
  action = Action('Get %s' % name, handler, {'group': group, 'order': next_seq()})
  
  Timer(lambda: action.call(), random(150, 190), random(5, 10))
  
@after_main
def bindProductInfo():
  group = 'Product Information'
  bindDevInfoCommand('Protocol Version', group, 'devinfo protocolver')
  bindDevInfoCommand('Parameter Set Version', group, 'devinfo paramsetver')
  bindDevInfoCommand('Firmware Version', group, 'devinfo version')
  bindDevInfoCommand('Product Name', group, 'devinfo productname')
  bindDevInfoCommand('Serial Number', group, 'devinfo serialno')
  bindDevInfoCommand('Device ID', group, 'devinfo deviceid')
  bindDevInfoCommand('Device Name', group, 'devinfo devicename')

#         --- SCP ---
  
def local_action_scpSetUTF8Encoding(arg=None):
  '''{"title": "Set UTF8 Encoding", "group": "SCP (protocol)", "order": 10001}'''
  tcp.request('scpmode encoding utf8', lambda resp: parseResp(resp))
  
def local_action_scpKeepAlive(arg):
  '''{"title": "Keep-Alive", "group": "SCP (protocol)", "order": 10002, "schema": {"type": "integer"}}'''
  tcp.request('scpmode keepalive %s' % int(arg), lambda resp: parseResp(resp))
  

#         --- Meters ---  

def local_action_meterStart(arg=None):
  '''{"title": "Meter Start", "group": "Meter", "order": 1, "schema": {"type": "object", "properties": {
                                               "address":   {"type": "string", "order": 1, "desc": "e.g. MTX:mtr_512/20000/meter"},
                                               "interval": {"type": "integer", "order": 3, "desc": "e.g. 333"}}}}'''
  # e.g. [mtrstart MTX:mtr_512/20000/meter 100]
  log(2, "MeterStart [%s]" % arg)
  tcp.request('mtrstart %s %s' % (arg['address'], arg['interval']),
              lambda resp: parseResp(resp))

# --- protocol>

  
# <tcp ---
  
def tcp_connected():
  console.info('tcp_connected')
  tcp.clearQueue()
  
  lookup_local_action('GetDeviceRunMode').call()
  
  # these seems to get no response if they're sent first,
  # so sending them after previous call
  lookup_local_action('scpSetUTF8Encoding').call()
  lookup_local_action('scpKeepAlive').call(30000)
  
def tcp_received(data):
  log(3, 'tcp_recv [%s]' % data)
  
  options = splitIntoOptions(data)
  
  # indicate a parsed packet (for status checking)
  lastReceive[0] = system_clock()
  
  option0 = options[0]
  
  if option0 == NOTIFY:
    
    option1 = options[1]
    
    if option1 == 'mtr':
      # deal with meters; pass on to a special meter handler
      handleNotifyMtr(options)
      
    elif option1 == 'set':
      # deal with parameters
      
      # e.g. [NOTIFY set MTX:mem_512/1/4/0/0/1/0 0 0 -75 "-75"]
      # so lookup the signal given the address
      addressPart = options[2]
      signalInfo = signalsByAddr.get(addressPart)

      if signalInfo == None:
        # unmapped
        return
       
      (converter, signal) = signalInfo

      parseResp(data, option=5, converter=converter, signal=signal)
      
    elif option1 == 'devstatus':
      # deal with device status categories

      # e.g.   NOTIFY devstatus fs "44.1kHz"        or
      #        NOTIFY devstatus lockstatus "lock"

      categoryPart = options[2] # e.g. 'fs'
      signalInfo = signalsByDevStatus.get(categoryPart)
      
      if signalInfo == None:
        return
      
      (converter, signal) = signalInfo
      
      parseResp(data, option=3, converter=converter, signal=signal)
      
  elif option0 == ERROR:
    local_event_LastCommsErrorTimestamp.emit(date_now())
  
def tcp_sent(data):
  log(3, 'tcp_sent [%s]' % data)
  
def tcp_disconnected():
  console.warn('tcp_disconnected')
  
def tcp_timeout():
  console.warn('tcp_timeout')

tcp = TCP(connected=tcp_connected, received=tcp_received, sent=tcp_sent, disconnected=tcp_disconnected, timeout=tcp_timeout)

# --- tcp>


# <logging ---

local_event_LogLevel = LocalEvent({'group': 'Debug', 'order': 10000+next_seq(), 'schema': {'type': 'integer'}})

def warn(level, msg):
  if local_event_LogLevel.getArg() >= level:
    console.warn(('  ' * level) + msg)

def log(level, msg):
  if local_event_LogLevel.getArg() >= level:
    console.log(('  ' * level) + msg)    

# --->


# <status and error reporting ---

local_event_LastCommsErrorTimestamp = LocalEvent({'title': 'Last Comms Error Timestamp', 'group': 'Status', 'order': 99999+next_seq(), 'schema': {'type': 'string'}})

# for comms drop-out
lastReceive = [0]

# roughly, the last contact  
local_event_LastContactDetect = LocalEvent({'group': 'Status', 'order': 99999+next_seq(), 'title': 'Last contact detect', 'schema': {'type': 'string'}})

# node status
local_event_Status = LocalEvent({'group': 'Status', 'order': 99999+next_seq(), 'schema': {'type': 'object', 'properties': {
        'level': {'type': 'integer', 'order': 1},
        'message': {'type': 'string', 'order': 2}}}})
  
def statusCheck():
  diff = (system_clock() - lastReceive[0])/1000.0 # (in secs)
  now = date_now()
  
  if diff > status_check_interval+15:
    previousContactValue = local_event_LastContactDetect.getArg()
    
    if previousContactValue == None:
      message = 'Always been missing.'
      
    else:
      previousContact = date_parse(previousContactValue)
      roughDiff = (now.getMillis() - previousContact.getMillis())/1000/60
      if roughDiff < 60:
        message = 'Missing for approx. %s mins' % roughDiff
      elif roughDiff < (60*24):
        message = 'Missing since %s' % previousContact.toString('h:mm:ss a')
      else:
        message = 'Missing since %s' % previousContact.toString('h:mm:ss a, E d-MMM')
      
    local_event_Status.emit({'level': 2, 'message': message})
    
  else:
    # update contact info
    local_event_LastContactDetect.emit(str(now))
    
    deviceErrorStatus = lookup_local_event('Device Error Status').getArg() or ''
    
    if deviceErrorStatus != 'none':
      # device is online but in bad state
      
      level = 1 if deviceErrorStatus.startswith('wrn') else 2
      
      local_event_Status.emit({'level': level, 'message': 'Device reports: [%s]' % deviceErrorStatus})
      
    else:
      # device is online and good
      local_event_LastContactDetect.emit(str(now))
      local_event_Status.emit({'level': 0, 'message': 'OK'})
    
status_check_interval = 75
status_timer = Timer(statusCheck, status_check_interval)

# --->


# <convenience methods ---

def getOrDefault(value, default):
  return default if is_blank(value) else value

from java.util import Random
_rand = Random()

# returns a random number between an interval
def random(fromm, to):
  return fromm + _rand.nextDouble()*(to - fromm)

# Splits into option (parts) dealing with quotes and escaping
#
# e.g. NOTIFY mtr MTX:mtr_512/20000/meter level 1b 1c 1c 1c 1b 1d 1d 1c 00 00 00 00 00 00 00 00
# or   OK devstatus runmode "normal"
#
# should return
#     ("NOTIFY", "mtf", ...)
# or  ("OK", "devstatus", "runmode", "normal")
def splitIntoOptions(line):
  parts = list()
  
  currentChars = list()
  escaping = False
  previousChar = None
  inQuotes = False
  
  for c in line:
    if escaping:
      # e.g. \" or \\
      currentChars.append(c)
      escaping = False
      
    elif c == '\\':
      escaping = True
      continue
    
    elif inQuotes:
      if c == '"':
        inQuotes = False
        parts.append(''.join(currentChars))
        del currentChars[:]
      
      else:
        currentChars.append(c)
        
    elif c == ' ':
      parts.append(''.join(currentChars))
      del currentChars[:]
      
    elif c == '"':
      inQuotes = True
      
    else:
      currentChars.append(c)
      
  if len(currentChars) > 0:
    parts.append(''.join(currentChars))
  
  return parts


# --->
