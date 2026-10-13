#!/usr/bin/env python3
"""Prepare exact sourcing/BOM review data, not a PCBA order or shipment instruction.

Run with KiCad Python against the sourced Product-D candidate. The output retains
pending SMT refs with blank codes and keeps the factory-tabbed cell in a separate
mandatory post-SMT list. No order quantities, attrition, stock, quote or receiving
address are invented. No generated CSV/RFQ/evidence belongs in Git.
"""
from pathlib import Path
import argparse,csv,hashlib,json
from seven_mm_sourcing import CONTRACT,ALL_REFS,PENDING,validate,inspect_fields,sha,require
from seven_mm_native_evidence import verify_native_clean
from _split_c1_common import REPO


def write_csv(path,headers,rows):
    with path.open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=headers,extrasaction='raise',lineterminator='\n')
        writer.writeheader();writer.writerows(rows)
    with path.open(encoding='utf-8-sig',newline='') as f:
        actual=list(csv.DictReader(f))
    require(len(actual)==len(rows), 'CSV row count mismatch: '+path.name)
    return actual


def export(candidate,output):
    candidate=Path(candidate).resolve();output=Path(output).resolve()
    require(not output.exists(), 'Choose a new sourcing delivery directory')
    require(not output.is_relative_to(REPO) or output.is_relative_to(REPO/'.work'), 'Generated output must stay external/ignored')
    plan=json.loads(CONTRACT.read_text());disposition=validate(plan)
    receipt=json.loads((candidate/'SOURCING-REBUILD.json').read_text())
    require(receipt['contract_sha256']==sha(CONTRACT), 'Rebuild used stale sourcing contract')
    physical,netlists=inspect_fields(candidate,plan)
    native={n:verify_native_clean(candidate/(n+'.kicad_pcb')) for n in ['Core','Display']}
    for name,e in native.items():
        require(e['pcb_sha256']==receipt['native'][name]['pcb_sha256'], 'Candidate changed after sourcing rebuild')
    all_rows=[]
    for r in sorted(physical,key=lambda v:(v['board'],v['ref'])):
        all_rows.append({'Board':r['board'],'Designator':r['ref'],'Manufacturer':r['manufacturer'],'MPN':r['mpn'],
            'Value':r['value'],'Footprint':r['footprint'],'LCSC Part #':r['lcsc'],
            'Quantity per board':1,'Assembly Stage':r['assembly_stage'],'Supply Route':r['supply_route'],
            'Supply Status':r['supply_status']})
    output.mkdir(parents=True)
    written=write_csv(output/'PCB-BOM-ALL-STAGES.csv',list(all_rows[0]),all_rows)
    require({r['Designator'] for r in written if r['Board']=='Core'}.issuperset(ALL_REFS), 'Lost a required reference in BOM export')
    for board in ['Core','Display']:
        items=[r for r in all_rows if r['Board']==board and r['Assembly Stage']=='SMT']
        write_csv(output/(board+'-SMT-BOM-REVIEW-NOT-RELEASED.csv'),list(all_rows[0]),items)
        if board=='Core':
            require({r['Designator'] for r in items if not r['LCSC Part #']}==set(PENDING), 'Pending SMT refs silently omitted')
            require(all(r['Designator']!='BT301' for r in items), 'Primary-cell assembly must not enter SMT BOM')
    review=[]
    for ref in sorted(disposition):
        r=disposition[ref]
        review.append({'Board':'Core','Designator':ref,'Old MPN':r.get('old_mpn',r['mpn']),
            'Current MPN':r['mpn'],'Manufacturer':r['manufacturer'],'LCSC Part #':r['lcsc'],
            'Package':r['package'],'Route':r['route'],'Assembly Stage':r['assembly_stage'],
            'Catalog Mapping':'VERIFIED' if r['lcsc'] else 'NOT ASSIGNED',
            'Supply Accepted':'NO','Source URL':r['source_url']})
    write_csv(output/'TWENTY-REFERENCE-DISPOSITION.csv',list(review[0]),review)
    registration=[]
    for r in plan['pending_registration']:
        registration.append({'Designators':','.join(r['refs']),'Qty per Core':len(r['refs']),
            'Manufacturer':r['manufacturer'],'Exact MPN':r['mpn'],'Package':r['package'],
            'JLC assigned code':'','Requested total qty':'TBD: boards x qty per Core + JLC-confirmed attrition',
            'Receiving address':'TBD: account-specific JLC consignment registration',
            'Submission':'PREPARED, NOT SUBMITTED','Supplier Channel':r['supplier_channel'],
            'Supplier Contact':r['contact'],'Source URL':r['source_url'],
            'Authorization URL':r['authorization_source'],'Variant Restriction':r['requirements']})
    write_csv(output/'JLC-REGISTRATION-REQUEST.csv',list(registration[0]),registration)
    manual=[r for r in all_rows if r['Assembly Stage']=='POST_SMT_MANUAL']
    require(len(manual)==1 and manual[0]['Designator']=='BT301','Missing/extra manual assembly')
    write_csv(output/'REQUIRED-POST-SMT.csv',list(all_rows[0]),manual)
    physical_refs={(r['board'],r['ref']) for r in physical}
    off=[]
    for board,info in netlists.items():
        for ref,c in info['comps'].items():
            if ref.startswith('#') or (board,ref) in physical_refs:continue
            # Non-physical/omitted solder terminals and test points are not new
            # purchasable components. The external thermal sensor is retained.
            if ref=='TH301':
                off.append({'Board':board,'Designator':ref,'Manufacturer':c['fields'].get('Manufacturer',''),
                    'MPN':c['fields'].get('MPN',''),'Value':c['value'],
                    'Assembly':'EXTERNAL NTC / retain original battery-temperature harness requirement'})
    if off:write_csv(output/'REQUIRED-OFFBOARD-NETLIST-PARTS.csv',list(off[0]),off)
    overview='''# Panda7 Product D — sourcing review, not a fabrication/assembly order

## 本轮结果

原先缺码的20个PCB位号：12个已核对并写入精确JLC目录代码；7个SMT位号仍需
取得实际JLC注册/客供接收；BT301为1个必须保留的后装电池组件，不能塞进回流焊BOM。
没有把“不贴装”、空白代码或准备好的询价表当作供料完成。没有下单、寄料、预留库存。

`TWENTY-REFERENCE-DISPOSITION.csv`逐位号列出原料号、现料号、代码和证据链接。
`PCB-BOM-ALL-STAGES.csv`来自更新后的实际PCB，包含BT301，不是整个机壳/屏幕的系统BOM。
两个`SMT-BOM-REVIEW-NOT-RELEASED.csv`是贴片审查表：Core仍有7个明确的空白代码，
不能作为已齐料的订单；Display的原有代码保持不变，本轮没有重新承诺所有旧料的库存。
`JLC-REGISTRATION-REQUEST.csv`含4种精确型号、每板用量、厂家/授权渠道和禁止替代项。
`REQUIRED-POST-SMT.csv`、`RFQ-BT301.md`确保电池后装不会丢失；另保留板外TH301要求。

## 下单数量和注册信息仍待输入

本次Core和Display各贴装多少块尚未确认。采购总量需按每板用量乘数量，并由嘉立创
确认贴装损耗/包装余量；这里没有擅自填5套或10套，也没有把一盘数量当成打样采购量。
必须先取得账户内的客供注册/仓库要求，再让大陆厂家或授权代理发货。不要直接寄到
网上找到的地址。以下RFQ为待发送草稿，不是报价、发货通知或收货凭证。

## 精确采购与替代约束

R540–R545明确从未核实的RC-02K0000FT改为风华RC-02000FT/C140225，仍为0402零欧姆；
不是把新代码附在旧料号上。Y501改为同厂、相同40MHz/12pF指标的
XL2EL89COI-111YLC-40M/C18214314。原厂YSX321SL焊盘/接脚图与实际封装核对，
C528/C529仍为18pF；C9010的15pF型号不能替代。全部网络、铜箔和设计规则未改变。

SGM2578SD必须保留SD/QOD版本；SGM62125必须保留A默认输出版本；SGM37601必须保留
20脚YTRL20封装；U22401必须保留-17沉板版本。不能通过这些替换去破坏电源/前光/接口。
BT301要求工厂制作的绝缘引线/焊片组件，不可回流焊或直接焊接裸电池；需要完整组件
图纸与高度审核，裸电池的目录代码不能证明该引线组件适用。RTC安全/24h保持验证仍开放。

## 当前检查范围

`SOURCING-NATIVE-EVIDENCE.json`来自重新填铜后的DRC/ERC/一致性检查。
目录身份不等于库存或供应商接收；整机公差、阻抗、RTC安全及板厂工艺等其他放行条件不因
本次BOM更新而自动通过。旧视频/模型是工程研究图，不能充当供料或装配确认。

官方流程：
'''+plan['consignment_policy_url']+'\n'+plan['global_sourcing_policy_url']+'\n'
    (output/'START-HERE.md').write_text(overview)
    sg=[r for r in plan['pending_registration'] if r['manufacturer']=='SGMICRO']
    sgrows='\n'.join(f"- {r['mpn']} | {r['package']} | {','.join(r['refs'])} | 每Core {len(r['refs'])}个" for r in sg)
    (output/'RFQ-SGMICRO.md').write_text('''# 待发送询价草稿：精确SGMICRO料号，供嘉立创SMT客供

收件渠道：SGMICRO中国销售/其官网列名的授权代理Sekorm。
联系人：sales_china@sg-micro.com；Sekorm 400-830-1766。
授权依据：https://www.sg-micro.com/authorized-distributors
状态：尚未发送、未得到报价/接收、未付款。总采购量待确定贴装数量及嘉立创损耗要求。

请确认以下精确料号可否提供原厂封装标签、批次/日期、MSL与干燥包装、剪带/整盘的
最小起订数量、交期及可追溯渠道，并支持发往订单指定的嘉立创大陆收料仓。
'''+sgrows+'''

不接受SGM2578S代替SGM2578SD；不接受SGM62125B/C/D代替A；不接受24脚SGM37601
代替20脚YTRL20。请回复确切供货后缀和原厂datasheet/包装图，勿仅回复系列名。
收货地址/标签由嘉立创账户实际客供登记生成；尚未提供，不得先寄料。
''')
    (output/'RFQ-MUP.md').write_text('''# 待发送询价草稿：MUP U22401-17沉板Type-C

收件：sales@mupconnector.com（MUP官网）；电话+86-755-29673656。
型号依据：https://www.mupconnector.com/product/usbc/3412.html
需求：每Core 1个，总数量待确认板数和SMT损耗；不是采购授权。

请报价精确U22401-17，16pin单排SMT、0.80mm沉板、NYLON、对应镀层版本；请提供当前
机械图/镀层与包装/壳脚图和MSL要求。需与现有9.24mm板槽及壳脚孔兼容，不能替换
为U20405顶装、-05或其他未审查后缀。请确认剪带/整盘最小数量、交期，以及对接嘉立创
客户物料注册的型号/包装要求。只有登记后才提供真实收货地址。未发送、未下单。
''')
    (output/'RFQ-JLC-REGISTRATION.md').write_text('''# 待提交嘉立创：4种精确客供物料注册

附件JLC-REGISTRATION-REQUEST.csv为7个必需SMT位号/4个型号组。请先确认账号内可用
物料编号、封装/贴装旋转、是否接受该精确料号、WLCSP检查要求及来料形式；再安排
厂家或授权代理按真实订单的收料标签/地址直寄。不得拿相似C码匹配，不得漏贴。

注册编号、订单数量、损耗余量、贴装接受、接收地址及到货记录均需真实回复，当前为空。
没有发送此申请或生成账号内客供单。裸板制造、受控阻抗和填孔盖铜仍需另行CAM接受。
''')
    (output/'RFQ-BT301.md').write_text('''# 待发送：BT301 CR1216工厂绝缘引线组件，不是裸电池贴片

厂家：Yichang Power Glory Technology Co., Ltd. / Omnergy。
依据：https://www.omnergybattery.com/product/cr1216-coin-button-cell-battery-for-remote-controls
每Core 1个；总数量待确认。要求厂家制作绝缘引线/焊片组件与图纸，非用户直接焊裸电池。

请提供组件最大厚度/直径、绝缘套/胶、焊片出线位置与极性、引线长度、线径、端部处理、
拉力/应力释放及批次资料。裸电芯标称3V/25mAh、直径12.5mm/厚1.6mm不能代表完整组件
最大外形。正线接RTC_CELL_P、负线接GND。必须在SMT及清洗完成后装配，不可回流焊或
直接焊接裸电池。该次需求尚未被厂家确认，且不替代RTC反向漏电/温度/24h保持测试。
''')
    (output/'SOURCING-NATIVE-EVIDENCE.json').write_text(json.dumps(native,indent=2)+'\n')
    manifest={'schema':'panda-seven-mm-sourcing-delivery-v1','contract_sha256':sha(CONTRACT),
              'native_source':{n:e['pcb_sha256'] for n,e in native.items()},'summary':plan['summary'],
              'required_pending_smt_refs':sorted(PENDING),'board_quantities_confirmed':False,
              'supplier_requests_submitted':False,'stock_reserved':False,'assembly_order_ready':False,
              'manufacturing_release':False,'files':{p.name:sha(p) for p in sorted(output.iterdir()) if p.is_file()}}
    (output/'DELIVERY-MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({'output':str(output),'physical_bom_rows':len(all_rows),'summary':plan['summary'],
                      'files':len(manifest['files']),'assembly_order_ready':False},ensure_ascii=False,indent=2))
    return manifest

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--candidate',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();export(args.candidate,args.output)
