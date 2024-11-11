#
# BSD 3-Clause License
#
# Copyright (c) 2021-2023, Fred W6BSD
# All rights reserved.
#
# For more information on the WSJT-X protocol look at the file
# NetworkMessage.hpp located in the wsjt-x source directory
# (src/wsjtx/Network/NetworkMessage.hpp)
#
# I use the camel case names to match the names in WSJT-X
# pylint: disable=invalid-name
#
# ******************************************************************
# ***** Some of the classes haven't been fully implemented and *****
# ***** need more work                                         *****
# ******************************************************************
#
# pylint: disable=consider-using-f-string,too-few-public-methods,too-many-public-methods

import ctypes
import struct
from datetime import datetime, timedelta
from enum import Enum

WS_MAGIC = 0xADBCCBDA
WS_SCHEMA = 2
WS_VERSION = '1.1'
WS_REVISION = '1a'
WS_CLIENTID = 'AUTOFS'


class Mode(Enum):
  FT8 = '~'
  FT4 = '+'

# Check the file


class PacketType(Enum):
  HEARTBEAT = 0                 # Out/in
  STATUS = 1                    # Out
  DECODE = 2                    # Out
  CLEAR = 3                     # Out/In
  REPLY = 4                     # In
  QSOLOGGED = 5                 # Out
  CLOSE = 6                     # Out/In
  REPLAY = 7                    # In
  HALTTX = 8                    # In
  FREETEXT = 9                  # In
  WSPRDECODE = 10               # Out
  LOCATION = 11                 # In
  LOGGEDADIF = 12               # Out
  HIGHLIGHTCALLSIGN = 13        # In
  SWITCHCONFIGURATION = 14      # In
  CONFIGURE = 15                # In


class Modifiers(Enum):
  NoModifier = 0x00
  SHIFT = 0x02
  CTRL = 0x04
  ALT = 0x08
  META = 0x10
  KEYPAD = 0x20
  GroupSwitch = 0x40


class SOMode(Enum):
  NONE = 0
  NA_VHF = 1
  EU_VHF = 2
  FIELD_DAY = 3
  RTTY_RU = 4
  WW_DIGI = 5
  FOX = 6
  HOUND = 7
  ARRL_DIGI = 8

  @classmethod
  def _missing_(cls, value):
    return cls.NONE


SHEAD = struct.Struct('!III')
JULIAN_ORIGIN = 2451545         # Julian date for 2000/01/01


class _WSPacket:

  def __init__(self, pkt=None):
    self._data = {}
    self._index = 0            # Keeps track of where we are in the packet parsing!

    if pkt is None:
      self._packet = ctypes.create_string_buffer(1023)
      self._magic_number = WS_MAGIC
      self._schema_version = WS_SCHEMA
      self._packet_type = 0
      self._client_id = WS_CLIENTID
    else:
      self._packet = ctypes.create_string_buffer(pkt, 1023)
      self._decode()

  def raw(self):
    try:
      self._encode()
    except struct.error as err:
      raise IOError(err) from None
    return self._packet[:self._index]

  def _decode(self):
    # in here depending on the Packet Type we create the class to handle the packet!
    magic, schema, pkt_type = SHEAD.unpack_from(self._packet)
    self._index += SHEAD.size
    self._magic_number = magic
    self._schema_version = schema
    self._packet_type = pkt_type
    self._client_id = self._get_string()

  def _encode(self):
    self._index = 0
    SHEAD.pack_into(self._packet, 0, self._magic_number,
                    self._schema_version, self._packet_type.value)
    self._index += SHEAD.size
    self._set_string(self._client_id)

  def __repr__(self):
    sbuf = [str(self.__class__)]
    for key, val in sorted(self._data.items()):
      sbuf.append("{}:{}".format(key, val))
    return ', '.join(sbuf)

  def _get_string(self):
    length = self._get_int32()
    # Empty strings have a length of zero whereas null strings have a
    # length field of 0xffffffff.
    if length == -1:
      return None
    fmt = '!{:d}s'.format(length)
    string, *_ = struct.unpack_from(fmt, self._packet, self._index)
    self._index += length
    return string.decode('utf-8')

  def _set_string(self, string):
    if string is None:
      self._set_int32(-1)
      return

    fmt = ''
    string = string.encode('utf-8')
    length = len(string)
    fmt = '!i{:d}s'.format(length)
    struct.pack_into(fmt, self._packet, self._index, length, string)
    self._index += struct.calcsize(fmt)

  def _get_datetime(self):
    time_offset = 0
    date_off = self._get_longlong()
    time_off = self._get_uint32()
    time_spec = self._get_byte()
    if time_spec == 2:
      time_offset = self._get_int32()
    return (date_off, time_off, time_spec, time_offset)

  def _set_datetime(self, value):
    date_off, time_off, time_spec, time_offset = value
    self._set_longlong(date_off)
    self._set_uint32(time_off)
    self._set_byte(time_spec)
    if time_spec == 2:
      self._set_uint32(time_offset)

  def _get_data(self, fmt):
    data, *_ = struct.unpack_from(fmt, self._packet, self._index)
    self._index += struct.calcsize(fmt)
    return data

  def _set_data(self, fmt, value):
    struct.pack_into(fmt, self._packet, self._index, value)
    self._index += struct.calcsize(fmt)

  def _get_byte(self):
    return self._get_data('!B')

  def _set_byte(self, value):
    self._set_data('!B', value)

  def _get_bool(self):
    return self._get_data('!?')

  def _set_bool(self, value):
    assert isinstance(value, (bool, int)), "Value should be bool or int"
    self._set_data('!?', value)

  def _get_int32(self):
    return self._get_data('!i')

  def _set_int32(self, value):
    self._set_data('!i', value)

  def _get_uint16(self):
    return self._get_data('!H')

  def _set_uint16(self, value):
    assert isinstance(value, int)
    self._set_data('!H', value)

  def _get_uint32(self):
    return self._get_data('!I')

  def _set_uint32(self, value):
    assert isinstance(value, int)
    self._set_data('!I', value)

  def _get_longlong(self):
    return self._get_data('!Q')

  def _set_longlong(self, value):
    assert isinstance(value, int)
    self._set_data('!Q', value)

  def _get_double(self):
    return self._get_data('!d')

  def _set_double(self, value):
    assert isinstance(value, float)
    self._set_data('!d', value)


class WSHeartbeat(_WSPacket):
  """Packet Type 0 Heartbeat (In/Out)"""

  def __init__(self, pkt=None):
    super().__init__(pkt)
    self._packet_type = PacketType.HEARTBEAT

  def __repr__(self):
    return "{} - Schema: {} Version: {} Revision: {}".format(
      self.__class__, self.MaxSchema, self.Version, self.Revision)

  def _decode(self):
    super()._decode()
    self._data['MaxSchema'] = self._get_uint32()
    self._data['Version'] = self._get_string()
    self._data['Revision'] = self._get_string()

  def _encode(self):
    self._packet_type = PacketType.HEARTBEAT
    super()._encode()
    self._set_uint32(self.MaxSchema)
    self._set_string(self.Version)
    self._set_string(self.Revision)

  @property
  def MaxSchema(self):
    return self._data.get('MaxSchema', WS_SCHEMA)

  @property
  def Version(self):
    return self._data.get('Version', WS_VERSION)

  @property
  def Revision(self):
    return self._data.get('Revision', WS_REVISION)


class WSStatus(_WSPacket):
  """Packet Type 1 Status  (Out)"""

  def __init__(self, pkt=None):
    super().__init__(pkt)
    self._packet_type = PacketType.STATUS

  def _decode(self):
    super()._decode()
    self._data['Frequency'] = self._get_longlong()
    self._data['Mode'] = self._get_string()
    self._data['DXCall'] = self._get_string()
    self._data['Report'] = self._get_string()
    self._data['TXMode'] = self._get_string()
    self._data['TXEnabled'] = self._get_bool()
    self._data['Transmitting'] = self._get_bool()
    self._data['Decoding'] = self._get_bool()
    self._data['RXdf'] = self._get_uint32()
    self._data['TXdf'] = self._get_uint32()
    self._data['DeCall'] = self._get_string()
    self._data['DeGrid'] = self._get_string()
    self._data['DEGrid'] = self._get_string()
    self._data['TXWatchdog'] = self._get_bool()
    self._data['SubMode'] = self._get_string()
    self._data['Fastmode'] = self._get_bool()
    self._data['SOMode'] = SOMode(self._get_byte())
    self._data['FreqTolerance'] = self._get_uint32()
    self._data['TRPeriod'] = self._get_uint32()
    self._data['ConfigName'] = self._get_string()
    self._data['TxMessage'] = self._get_string()

  @property
  def Frequency(self):
    return self._data['Frequency']

  @property
  def Mode(self):
    return Mode(self._data['Mode']).name

  @property
  def DXCall(self):
    return self._data['DXCall']

  @property
  def Report(self):
    return self._data['Report']

  @property
  def TXMode(self):
    return self._data['TXMode']

  @property
  def TXEnabled(self):
    return self._data['TXEnabled']

  @property
  def Transmitting(self):
    return self._data['Transmitting']

  @property
  def Decoding(self):
    return self._data['Decoding']

  @property
  def RXdf(self):
    return self._data['RXdf']

  @property
  def TXdf(self):
    return self._data['TXdf']

  @property
  def DeCall(self):
    return self._data['DeCall']

  @property
  def DeGrid(self):
    return self._data['DeGrid']

  @property
  def DEGrid(self):
    return self._data['DEGrid']

  @property
  def TXWatchdog(self):
    return self._data['TXWatchdog']

  @property
  def SubMode(self):
    return self._data['SubMode']

  @property
  def Fastmode(self):
    return self._data['Fastmode']

  @property
  def SOMode(self):
    return self._data['SOMode']

  @property
  def reqTolerance(self):
    return self._data['reqTolerance']

  @property
  def RPeriod(self):
    return self._data['RPeriod']

  @property
  def onfigName(self):
    return self._data['onfigName']

  @property
  def xMessage(self):
    return self._data['xMessage']


class WSDecode(_WSPacket):
  """Packet Type 2  Decode  (Out)"""

  def __init__(self, pkt=None):
    super().__init__(pkt)
    self._packet_type = PacketType.DECODE

  def _decode(self):
    super()._decode()
    self._data['New'] = self._get_bool()
    self._data['Time'] = wstime2datetime(self._get_uint32())
    self._data['SNR'] = self._get_int32()
    self._data['DeltaTime'] = round(self._get_double(), 3)
    self._data['DeltaFrequency'] = self._get_uint32()
    self._data['Mode'] = self._get_string()
    self._data['Message'] = self._get_string()
    self._data['LowConfidence'] = self._get_bool()
    self._data['OffAir'] = self._get_bool()

  def as_dict(self):
    return self._data

  @property
  def New(self):
    return self._data['New']

  @property
  def Time(self):
    return self._data['Time']

  @property
  def SNR(self):
    return self._data['SNR']

  @property
  def DeltaTime(self):
    return self._data['DeltaTime']

  @property
  def DeltaFrequency(self):
    return self._data['DeltaFrequency']

  @property
  def Mode(self):
    return Mode(self._data['Mode']).name

  @property
  def Message(self):
    return self._data['Message']

  @property
  def LowConfidence(self):
    return self._data['LowConfidence']

  @property
  def OffAir(self):
    return self._data['OffAir']


class WSClear(_WSPacket):
  """Packet Type 3  Clear (Out/In)"""

  def __init__(self, pkt=None):
    super().__init__(pkt)
    self._packet_type = PacketType.CLEAR

  def _decode(self):
    super()._decode()
    self._data['Window'] = None
    if self._index < len(self._packet):
      self._data['Window'] = self._get_byte()

  @property
  def Window(self):
    return self._data['Window']


class WSReply(_WSPacket):
  """
  Packet Type 4 Reply (In)
  * Id (target unique key) utf8
  * Time                   quint (QTime)
  * snr                    qint32
  * Delta time (S)         float (serialized as double)
  * Delta frequency (Hz)   quint32
  * Mode                   utf8
  * Message                utf8
  * Low confidence         bool
  * Modifiers              quint8
  """

  def __init__(self, pkt=None):
    super().__init__(pkt)
    self._packet_type = PacketType.REPLY
    self._client_id = "AUTOFT"

  def _encode(self):
    super()._encode()
    self._set_uint32(datetime2wstime(self._data['Time']))
    self._set_int32(self._data['SNR'])
    self._set_double(self._data['DeltaTime'])
    self._set_uint32(self._data['DeltaFrequency'])
    self._set_string(self._data['Mode'])
    self._set_string(self._data['Message'])
    self._set_bool(self._data.get('LowConfidence', False))
    self._set_byte(self._data.get('Modifiers', Modifiers.NoModifier.value))

  @property
  def Time(self):
    return self._data.get('Time')

  @Time.setter
  def Time(self, val):
    assert isinstance(val, datetime), 'Object datetime expected'
    self._data['Time'] = val

  @property
  def SNR(self):
    return self._data.get('SNR')

  @SNR.setter
  def SNR(self, val):
    self._data['SNR'] = int(val)

  @property
  def DeltaTime(self):
    return self._data.get('DeltaTime')

  @DeltaTime.setter
  def DeltaTime(self, val):
    self._data['DeltaTime'] = float(val)

  @property
  def DeltaFrequency(self):
    return self._data.get('DeltaFrequency')

  @DeltaFrequency.setter
  def DeltaFrequency(self, val):
    self._data['DeltaFrequency'] = int(val)

  @property
  def Mode(self):
    return Mode(self._data.get('Mode')).name

  @Mode.setter
  def Mode(self, val):
    if len(val) == 1:
      self._data['Mode'] = val
    else:
      self._data['Mode'] = getattr(Mode, val).value

  @property
  def Message(self):
    return self._data.get('Message')

  @Message.setter
  def Message(self, val):
    self._data['Message'] = val

  @property
  def LowConfidence(self):
    return self._data.get('LowConfidence')

  @LowConfidence.setter
  def LowConfidence(self, val):
    self._data['LowConfidence'] = bool(val)

  @property
  def Modifiers(self):
    return self._data.get('Modifiers', Modifiers.NoModifier)

  @Modifiers.setter
  def Modifiers(self, modifier):
    assert isinstance(modifier, Modifiers)
    self._data['Modifiers'] = modifier.value


class WSLogged(_WSPacket):
  """Packet Type 5 QSO Logged (Out)"""

  def __init__(self, pkt=None):
    super().__init__(pkt)
    self._packet_type = PacketType.QSOLOGGED

  def _decode(self):
    super()._decode()
    self._data['DateTimeOff'] = self._get_datetime()
    self._data['DXCall'] = self._get_string()
    self._data['DXGrid'] = self._get_string()
    self._data['DialFrequency'] = self._get_longlong()
    self._data['Mode'] = self._get_string()
    self._data['ReportSent'] = self._get_string()
    self._data['ReportReceived'] = self._get_string()
    self._data['TXPower'] = self._get_string()
    self._data['Comments'] = self._get_string()
    self._data['Name'] = self._get_string()
    self._data['DateTimeOn'] = self._get_datetime()
    self._data['OpCall'] = self._get_string()
    self._data['MyCall'] = self._get_string()
    self._data['MyGrid'] = self._get_string()
    self._data['ExSent'] = self._get_string()
    self._data['ExReceived'] = self._get_string()
    self._data['PropMode'] = self._get_string()

  def _encode(self):
    super()._encode()
    self._set_datetime(self._data['DateTimeOff'])
    self._set_string(self._data['DXCall'])
    self._set_string(self._data['DXGrid'])
    self._set_longlong(self._data['DialFrequency'])
    self._set_string(self._data['Mode'])
    self._set_string(self._data['ReportSent'])
    self._set_string(self._data['ReportReceived'])
    self._set_string(self._data.get('TXPower'))
    self._set_string(self._data.get('Comments'))
    self._set_string(self._data.get('Name', ''))
    self._set_datetime(self._data['DateTimeOn'])
    self._set_string(self._data.get('OpCall', ''))
    self._set_string(self._data.get('MyCall', ''))
    self._set_string(self._data.get('MyGrid', ''))
    self._set_string(self._data.get('ExSent', ''))
    self._set_string(self._data.get('ExReceived', ''))
    self._set_string(self._data.get('PropMode', ''))

  @property
  def DateTimeOff(self):
    return from_julian(*self._data['DateTimeOff'])

  @DateTimeOff.setter
  def DateTimeOff(self, val):
    assert isinstance(val, datetime)
    self._data['DateTimeOff'] = to_julian(val)

  @property
  def DXCall(self):
    return self._data['DXCall']

  @DXCall.setter
  def DXCall(self, val):
    self._data['DXCall'] = val

  @property
  def DXGrid(self):
    return self._data['DXGrid']

  @DXGrid.setter
  def DXGrid(self, val):
    self._data['DXGrid'] = val

  @property
  def DialFrequency(self):
    return self._data['DialFrequency']

  @DialFrequency.setter
  def DialFrequency(self, val):
    self._data['DialFrequency'] = val

  @property
  def Mode(self):
    return Mode[self._data['Mode']].value

  @Mode.setter
  def Mode(self, val):
    assert isinstance(val, str)
    try:
      self._data['Mode'] = getattr(Mode, val).value
    except AttributeError:
      self._data['Mode'] = val

  @property
  def ReportSent(self):
    return self._data['ReportSent']

  @ReportSent.setter
  def ReportSent(self, val):
    self._data['ReportSent'] = val

  @property
  def ReportReceived(self):
    return self._data['ReportReceived']

  @ReportReceived.setter
  def ReportReceived(self, val):
    self._data['ReportReceived'] = val

  @property
  def TXPower(self):
    return self._data['TXPower']

  @TXPower.setter
  def TXPower(self, val):
    if isinstance(val, (int, float)):
      val = str(val)
    self._data['TXPower'] = val

  @property
  def Comments(self):
    return self._data['Comments']

  @Comments.setter
  def Comments(self, val):
    self._data['Comments'] = val

  @property
  def Name(self):
    return self._data['Name']

  @Name.setter
  def Name(self, val):
    self._data['Name'] = val

  @property
  def DateTimeOn(self):
    return from_julian(*self._data['DateTimeOn'])

  @DateTimeOn.setter
  def DateTimeOn(self, val):
    self._data['DateTimeOn'] = to_julian(val)

  @property
  def OpCall(self):
    return self._data['OpCall']

  @OpCall.setter
  def OpCall(self, val):
    self._data['OpCall'] = val

  @property
  def MyCall(self):
    return self._data['MyCall']

  @MyCall.setter
  def MyCall(self, val):
    self._data['MyCall'] = val

  @property
  def MyGrid(self):
    return self._data['MyGrid']

  @MyGrid.setter
  def MyGrid(self, val):
    self._data['MyGrid'] = val

  @property
  def ExSent(self):
    return self._data['ExSent']

  @ExSent.setter
  def ExSent(self, val):
    self._data['ExSent'] = val

  @property
  def ExReceived(self):
    return self._data['ExReceived']

  @ExReceived.setter
  def ExReceived(self, val):
    self._data['ExReceived'] = val

  @property
  def PropMode(self):
    return self._data['PropMode']

  @PropMode.setter
  def PropMode(self, val):
    self._data['PropMode'] = val


class WSClose(_WSPacket):
  """Packet Type 6 Close (Out/In)"""

  def __init__(self, pkt=None):
    super().__init__(pkt)
    self._packet_type = PacketType.CLOSE


class WSReplay(_WSPacket):
  """Packet Type 7 Replay (In)"""

  def __init__(self, pkt=None):
    super().__init__(pkt)
    self._packet_type = PacketType.REPLAY


class WSHaltTx(_WSPacket):
  """Packet Type 8 Halt Tx (In)
  self.mode = True
      Will stop the transmission at the end of the sequency
  self.mode = False
      Will stop the transmission immediately
  """

  def __init__(self, pkt=None):
    super().__init__(pkt)
    self._packet_type = PacketType.HALTTX
    self._data['mode'] = False

  def _encode(self):
    super()._encode()
    self._set_bool(self._data['mode'])

  @property
  def mode(self):
    return self._data['mode']

  @mode.setter
  def mode(self, val):
    assert isinstance(val, bool)
    self._data['mode'] = val


class WSFreeText(_WSPacket):
  """Packet Type 9 Free Text (In)"""

  def __init__(self, pkt=None):
    super().__init__(pkt)
    self._packet_type = PacketType.FREETEXT

  def _encode(self):
    super()._encode()
    self._set_string(self._data.get('text', ''))
    self._set_bool(self._data.get('send', True))

  @property
  def text(self):
    return self._data.get('text', '')

  @text.setter
  def text(self, val):
    assert isinstance(val, str), 'Expecting a string'
    self._data['text'] = val

  @property
  def send(self):
    return self._data.get('send', True)

  @send.setter
  def send(self, val):
    assert isinstance(val, bool), 'Expecting a boolean'
    self._data['send'] = val


class WSWSPRDecode(_WSPacket):
  """Packet Type 10 WSPR Decode (Out)"""

  def __init__(self, pkt=None):
    super().__init__(pkt)
    self._packet_type = PacketType.WSPRDECODE


class WSLocation(_WSPacket):
  """Packet Type 11 Location (In)"""

  def __init__(self, pkt=None):
    super().__init__(pkt)
    self._packet_type = PacketType.LOCATION


class WSADIF(_WSPacket):
  """Packet Type 12 Logged ADIF (Out)"""

  def __init__(self, pkt=None):
    super().__init__(pkt)
    self._packet_type = PacketType.LOGGEDADIF

  def _decode(self):
    super()._decode()
    self._data['ADIF'] = self._get_string()

  def __str__(self):
    return ''.join(self._data['ADIF'].split('\n'))

  def __repr__(self):
    if 'ADIF' in self._data:
      return "{} {}".format(self.__class__, self._data['ADIF'])
    return "{} {}".format(self.__class__, self._packet.raw)

  @property
  def Id(self):
    return self._data['Id']

  @property
  def ADIF(self):
    return self._data['ADIF']


class WSHighlightCallsign(_WSPacket):
  """
  Packet Type 13 Highlight Callsign (In)
  Callsign               utf8
  Background Color       QColor
  Foreground Color       QColor
  Highlight last         bool
  """

  def __init__(self, pkt=None):
    super().__init__(pkt)
    self._packet_type = PacketType.HIGHLIGHTCALLSIGN

  def _encode(self):
    super()._encode()
    self._set_string(self._data['call'])

    self._set_uint16(0xffff)
    for val in self._data.get('Foreground', (0xffff, 0xff, 0xff)):
      self._set_uint16(val)

    self._set_uint16(0xffff)
    for val in self._data.get('Background', (0, 0, 0)):
      self._set_uint16(val)

    self._set_bool(self._data.get('HighlightLast', True))

  def __repr__(self):
    return "{} call: {}".format(self.__class__, self._data.get('call', 'NoCall'))

  @property
  def call(self):
    return self._data['call']

  @call.setter
  def call(self, call):
    assert isinstance(call, str), 'The callsign must be a string'
    self._data['call'] = call

  @property
  def Background(self):
    return self._data['Background']

  @Background.setter
  def Background(self, rgb):
    assert isinstance(rgb, (list, tuple)), "Tuple object expected"
    self._data['Background'] = rgb

  @property
  def Foreground(self):
    return self._data['Foreground']

  @Foreground.setter
  def Foreground(self, rgb):
    assert isinstance(rgb, (list, tuple)), "Tuple object expected"
    self._data['Foreground'] = rgb

  @property
  def HighlightLast(self):
    return self._data['HighlightLast']

  @HighlightLast.setter
  def HighlightLast(self, val):
    self._data['HighlightLast'] = bool(val)


class WSSwitchConfiguration(_WSPacket):
  """Packet Type 14 Switch Configuration (In)"""

  def __init__(self, pkt=None):
    super().__init__(pkt)
    self._packet_type = PacketType.SWITCHCONFIGURATION


class WSConfigure(_WSPacket):
  """Packet Type 15 Configure (In)"""

  def __init__(self, pkt=None):
    super().__init__(pkt)
    self._packet_type = PacketType.CONFIGURE


def from_julian(jday, msec, *_):
  # this function doesn't work with dates prior to 2000
  epoch = datetime(2000, 1, 1)
  tdelta = timedelta(days=jday - JULIAN_ORIGIN)
  day = epoch + tdelta
  dtime = day + timedelta(microseconds=msec * 1000)
  return dtime


def to_julian(dtime):
  # this function doesn't work with dates prior to 2000
  epoch = datetime(2000, 1, 1)
  delta = dtime - epoch
  jday = delta.days + JULIAN_ORIGIN
  milliseconds = int(delta.seconds * 1000)
  return (jday, milliseconds, 1, 0)


def wstime2datetime(qtm):
  """wsjtx time containd the number of milliseconds since midnight"""
  tday_midnight = datetime.combine(datetime.utcnow(), datetime.min.time())
  return tday_midnight + timedelta(milliseconds=qtm)


def datetime2wstime(dtime):
  """wsjtx time containd the number of milliseconds since midnight"""
  tday_midnight = datetime.combine(datetime.utcnow(), datetime.min.time())
  return int((dtime - tday_midnight).total_seconds() * 1000)


def ft8_decode(pkt):
  """Look at the packets header and return a class corresponding to the packet"""
  magic, _, pkt_type = SHEAD.unpack_from(pkt)
  if magic != WS_MAGIC:
    raise IOError('Not a WSJT-X packet')

  switch_map = {
    PacketType.HEARTBEAT.value: WSHeartbeat,
    PacketType.STATUS.value: WSStatus,
    PacketType.DECODE.value: WSDecode,
    PacketType.CLEAR.value: WSClear,
    PacketType.REPLY.value: WSReply,
    PacketType.QSOLOGGED.value: WSLogged,
    PacketType.CLOSE.value: WSClose,
    PacketType.LOGGEDADIF.value: WSADIF,
    PacketType.HIGHLIGHTCALLSIGN.value: WSHighlightCallsign,
  }

  try:
    return switch_map[pkt_type](pkt)
  except KeyError:
    raise NotImplementedError("Packet type '{:d}' unknown".format(pkt_type)) from None
