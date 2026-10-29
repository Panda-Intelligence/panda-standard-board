"""在隔离试验板中使用 KiCad 0603 标准封装，保留 C501 的原生身份与网络。"""
import sys
from pathlib import Path
import pcbnew as p


def main(board_file, stock_library, local_library):
    board = p.LoadBoard(board_file)
    old = board.FindFootprintByReference('C501')
    if old is None:
        raise ValueError('找不到 C501')
    new = p.FootprintLoad(stock_library, 'C_0603_1608Metric')
    if new is None:
        raise ValueError('找不到 KiCad 标准 0603 封装')
    old_pads = {pad.GetNumber(): (pad.GetNetname(), pad.m_Uuid.AsString()) for pad in old.Pads()}
    if set(old_pads) != {'1', '2'} or {x.GetNumber() for x in new.Pads()} != {'1', '2'}:
        raise ValueError('C501 焊盘编号不匹配')
    fields = old.GetFieldsText()
    new.SetFields(fields)
    for key, val in (('Manufacturer', 'FH (Fenghua Advanced)'), ('MPN', '0603X226M100NT'), ('LCSC', 'C60077')):
        new.SetField(key, val)
        f = new.GetFieldByName(key)
        if f is not None:
            f.SetVisible(False)
    new.SetField('Description', 'FH 22uF 10V X5R +/-20% 0603 local bypass for ESP32-S3 3V3_AON; DC-bias capacitance remains physical qualification.')
    new.SetPath(old.GetPath())
    new.SetPosition(old.GetPosition())
    new.SetOrientationDegrees(old.GetOrientationDegrees())
    new.SetAttributes(old.GetAttributes())
    new.SetFPIDAsString('Panda47:C501_Core')
    new.m_Uuid.Clone(p.KIID(old.m_Uuid.AsString()))
    board.Remove(old)
    board.Add(new)
    for pad in new.Pads():
        net, uuid = old_pads[pad.GetNumber()]
        net_info = board.FindNet(net)
        if net_info is None:
            raise ValueError('C501 网络不存在：' + net)
        pad.SetNet(net_info)
        pad.m_Uuid.Clone(p.KIID(uuid))
    if not Path(local_library).is_dir():
        raise ValueError('试验板的本地封装库不存在')
    p.FootprintSave(local_library, new)
    board.Save(board_file)
    print('C501 标准 0603 试验封装已写入；实际料号和 DC bias 待验证')


if __name__ == '__main__':
    main(*sys.argv[1:])
