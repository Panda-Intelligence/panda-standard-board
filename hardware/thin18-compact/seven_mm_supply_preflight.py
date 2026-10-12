#!/usr/bin/env python3
"""Native-bound supplier registration preflight; never a purchase or stock claim.

Public search evidence, component geometry, quantities and actual warehouse
availability are separate. No writes to native CAD or supplier accounts occur.
"""
from pathlib import Path
import argparse, csv, hashlib, json, re
from seven_mm_sourcing import CONTRACT as SOURCING, validate as validate_sourcing, PENDING, inspect_fields
from seven_mm_native_evidence import verify_native_clean
from _split_c1_common import ROOT, REPO

CONTRACT = ROOT/'seven_mm_supply_registration.json'
MSL = {'SGM2578SDYG/TR':1, 'SGM62125AXG/TR':1, 'SGM37601YTRL20G/TR':2, 'U22401-17':None}
STATUS = {'Reviewing','Awaiting Confirmation','Awaiting Payment','Shipped','Received','Checked','In Warehouse','Cancelled'}
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
def require(ok, message):
    if not ok: raise ValueError(message)
def positive_integer(value):
    return isinstance(value,int) and not isinstance(value,bool) and value > 0

def validate(plan):
    require(plan['schema']=='panda-seven-mm-registration-technical-v1','Wrong technical request schema')
    require(plan['source_sourcing_sha256']==sha(SOURCING),'Stale sourcing predecessor')
    require(all(plan[k] is False for k in ['supplier_inquiries_sent','orders_submitted','manufacturing_release']), 'Do not manufacture submission or release evidence')
    refs=[]
    for row in plan['request_lines']:
        require(row['board']=='Core' and row['assembly_stage']=='SMT','Wrong physical assembly stage')
        require(row['qty_per_core']==len(row['refs']) and positive_integer(row['qty_per_core']),'Wrong per-board quantity')
        require(row['mpn'] in MSL,'Unreviewed part in MSL table')
        require(row['moisture_sensitivity_level'] is None or (isinstance(row['moisture_sensitivity_level'],int) and not isinstance(row['moisture_sensitivity_level'],bool)), 'Invalid MSL type')
        require(row['moisture_sensitivity_level']==MSL[row['mpn']],'Wrong manufacturer MSL/variant')
        for ref in row['refs']:
            require(ref in PENDING and (row['manufacturer'],row['mpn'],row['package'])==PENDING[ref],'Unreviewed variant or omitted required part')
            refs.append(ref)
        require(all(row[k] is None for k in ['catalog_code','registration_id','account_warehouse_address']), 'Unproven account-specific data in source template')
        require(all(row[k] is False for k in ['submitted','received','accepted']), 'A template is not an order response')
    require(len(refs)==len(set(refs))==7 and set(refs)==set(PENDING),'All seven SMT references must remain')
    c=plan['rtc_assembly_request']
    require(c['ref']=='BT301' and c['cell_mpn']=='CR1216' and c['internal_id_is_not_a_vendor_sku'] is True,'Wrong cell identity')
    require(c['assembly_stage']=='POST_SMT_MANUAL' and c['factory_assembly_part_number'] is None,'No unconfirmed battery orderable assembly')
    require(c['installed_height_budget_above_pcb_mm']==2.4 and c['budget_is_not_supplier_maximum'] is True,'Unreviewed installed-cell budget')
    require(c['existing_pads_lie_under_cell_body'] is True,'Do not hide the required lead assembly sequence')
    for k in ['reflow_allowed','bare_cell_direct_solder_allowed','drawing_accepted','polarity_and_insulation_inspected','reverse_charge_and_retention_qualified']:
        require(c[k] is False,'Unproven battery safety or mechanical acceptance')
    require(c['positive_native_pad']=={'number':'1','net':'RTC_CELL_P','xy_mm':[58.5,56.4],'size_mm':[2,2]},'Wrong battery positive landing')
    require(c['negative_native_pad']=={'number':'2','net':'GND','xy_mm':[68.5,56.4],'size_mm':[2,2]},'Wrong battery negative landing')
    rejected={r['jlc_code']:r for r in plan['rejected_or_unapproved_catalog_candidates']}
    require(set(rejected)=={'C49325733','C56127182','C9900262011','C5128294'},'Missing variant review')
    require(rejected['C49325733']['candidate_mid_mount_mm']==1.6 and rejected['C49325733']['required_mid_mount_mm']==.8,'Wrong connector mounting datum')
    require(all(r['decision'] in {'REJECTED_FOR_CURRENT_GEOMETRY','NOT_APPROVED_REPLACEMENT','INSUFFICIENT_EXACT_IDENTITY'} for r in rejected.values()),'Unreviewed catalog candidate approved')
    proof=plan['catalog_recheck']
    require(proof['positive_control']=={'keyword':'C74301','matched_mpn':'SDCL1005C24NJTDF','matched_code':'C74301'},'Missing valid search control')
    require(re.fullmatch('[a-f0-9]{64}',proof['evidence_sha256']) is not None,'Missing search evidence binding')
    return True

def required_quantities(plan, core_count=None, display_count=None, attrition=None):
    for count in [core_count,display_count]:
        require(count is None or positive_integer(count),'Board quantity must be a positive integer, not a default guess')
    attrition={} if attrition is None else attrition
    known={r['mpn'] for r in plan['request_lines']}
    require(not(set(attrition)-known),'Attrition includes an unexpected part')
    rows=[]
    for r in plan['request_lines']:
        extra=attrition.get(r['mpn'])
        require(extra is None or (isinstance(extra,int) and not isinstance(extra,bool) and extra>=0),'Invalid JLC attrition quantity')
        population=None if core_count is None else core_count*r['qty_per_core']
        rows.append({'mpn':r['mpn'],'refs':r['refs'],'per_core':r['qty_per_core'],'population_qty':population,
                     'jlc_confirmed_attrition_qty':extra,'requested_total':None if population is None or extra is None else population+extra})
    return rows

def warehouse_usable(status, available, required, *, exact_identity_reviewed=False, document_reviewed=False):
    """State consistency only, NOT authentication of any external document."""
    require(status in STATUS,'Unknown JLC state')
    require(isinstance(available,int) and not isinstance(available,bool) and available>=0,'Invalid available quantity')
    require(positive_integer(required),'Invalid required quantity')
    require(type(exact_identity_reviewed) is bool and type(document_reviewed) is bool,'Review inputs must be booleans')
    return status=='In Warehouse' and available>=required and exact_identity_reviewed and document_reviewed

def native_reference(candidate, plan):
    import wx
    app=wx.GetApp() or wx.App(False)
    import pcbnew as P
    board=P.LoadBoard(str(candidate/'Core.kicad_pcb'));parts=[];pins=[]
    requested={ref:r for r in plan['request_lines'] for ref in r['refs']}
    requested['BT301']={'mpn':'CR1216','manufacturer':plan['rtc_assembly_request']['manufacturer'],'assembly_stage':'POST_SMT_MANUAL'}
    xy=lambda p:[round(P.ToMM(p.x),6),round(P.ToMM(p.y),6)]
    for ref,r in sorted(requested.items()):
        f=board.FindFootprintByReference(ref);require(f is not None and not f.IsDNP() and not f.IsExcludedFromBOM(),'Required physical component missing '+ref)
        fields={x.GetName():x.GetText() for x in f.GetFields()}
        require(fields.get('MPN')==r['mpn'] and fields.get('Manufacturer')==r['manufacturer'],'Native part identity differs '+ref)
        parts.append({'Ref':ref,'Manufacturer':r['manufacturer'],'Exact MPN':r['mpn'],'Assembly Stage':r['assembly_stage'],
                      'Native X mm':xy(f.GetPosition())[0],'Native Y mm':xy(f.GetPosition())[1],'Native Angle deg':f.GetOrientationDegrees(),
                      'Side':board.GetLayerName(f.GetLayer()),'Angle meaning':'KiCad F-side top view; JLC machine rotation MUST be confirmed against exact footprint/drawing'})
        for p in f.Pads():
            if not p.GetNumber():continue  # TQFN paste windows are not more pins.
            pins.append({'Ref':ref,'Pad':p.GetNumber(),'Net':str(p.GetNetname()),'Pin function':p.GetPinFunction(),
                         'X mm':xy(p.GetPosition())[0],'Y mm':xy(p.GetPosition())[1],
                         'Pad width mm':xy(p.GetSize())[0],'Pad height mm':xy(p.GetSize())[1],
                         'Drill X mm':xy(p.GetDrillSize())[0],'Drill Y mm':xy(p.GetDrillSize())[1]})
    bt=[r for r in pins if r['Ref']=='BT301']
    for name in ['positive_native_pad','negative_native_pad']:
        expected=plan['rtc_assembly_request'][name];p=next(r for r in bt if r['Pad']==expected['number'])
        require(p['Net']==expected['net'] and [p['X mm'],p['Y mm']]==expected['xy_mm'] and [p['Pad width mm'],p['Pad height mm']]==expected['size_mm'],'Cell request no longer matches actual PCB')
    require(len([p for p in pins if p['Ref']=='U905'])==21,'TQFN20 includes exactly one named exposed pad')
    return parts,pins

def write_csv(path, rows):
    require(bool(rows),'No rows in requested CSV')
    with path.open('w',encoding='utf-8-sig',newline='') as f:
        wr=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');wr.writeheader();wr.writerows(rows)

def export(candidate, output, core_count=None, display_count=None):
    candidate=Path(candidate).resolve();output=Path(output).resolve()
    require(not output.exists(),'Choose a fresh output directory')
    require(not output.is_relative_to(REPO) or output.is_relative_to(REPO/'.work'),'Generated files must remain external/ignored')
    plan=json.loads(CONTRACT.read_text());validate(plan)
    sourcing=json.loads(SOURCING.read_text());validate_sourcing(sourcing);inspect_fields(candidate,sourcing)
    receipt=json.loads((candidate/'SOURCING-REBUILD.json').read_text());require(receipt['contract_sha256']==sha(SOURCING),'Stale native sourcing overlay')
    native={n:verify_native_clean(candidate/(n+'.kicad_pcb')) for n in ['Core','Display']}
    require(all(native[n]['pcb_sha256']==receipt['native'][n]['pcb_sha256'] for n in native),'Native candidate changed after sourcing validation')
    parts,pins=native_reference(candidate,plan);quant=required_quantities(plan,core_count,display_count)
    output.mkdir(parents=True)
    write_csv(output/'NATIVE-PLACEMENT-REFERENCE-NOT-MACHINE-CPL.csv',parts)
    write_csv(output/'NATIVE-PIN-MAP.csv',pins)
    rows=[]
    for r,q in zip(plan['request_lines'],quant):
        rows.append({'Refs':','.join(r['refs']),'Manufacturer':r['manufacturer'],'Exact MPN':r['mpn'],'Package':r['package'],
                     'Qty per Core':r['qty_per_core'],'Confirmed Core quantity':core_count or '',
                     'Population quantity':q['population_qty'] if q['population_qty'] is not None else '',
                     'JLC-confirmed attrition':'','Required shipment quantity':'','MSL':r['moisture_sensitivity_level'] or 'Manufacturer confirmation required',
                     'Exact catalog or registered code':'','Part registration accepted':'NO','Receiving instructions':'Account-specific, not issued',
                     'Manufacturer datasheet':r['datasheet'],'Quote status':'NOT REQUESTED / NO ACCEPTANCE'})
    write_csv(output/'EXACT-PART-REGISTRATION.csv',rows)
    write_csv(output/'USB-CANDIDATE-REJECTION.csv',[{'Requested':r['requested_mpn'],'Candidate':r['candidate_mpn'],'Candidate code':r['jlc_code'],
       'Decision':r['decision'],'Reason':r['reason'],'Manufacturer source':r.get('manufacturer_url',''),'Catalog source':r.get('catalog_url','')} for r in plan['rejected_or_unapproved_catalog_candidates']])
    # The request is intentionally not a manufacturer assembly drawing or receipt.
    cell=plan['rtc_assembly_request']
    (output/'BT301-FACTORY-DRAWING-REQUEST.json').write_text(json.dumps(cell,ensure_ascii=False,indent=2)+'\n')
    template={'record_type':'UNFILLED_TEMPLATE_NOT_A_RECEIPT','board_quantities':{'Core':core_count,'Display':display_count},
       'account_owner_confirmation':None,'request_send_authorized':False,
       'lines':[{'manufacturer':r['manufacturer'],'exact_mpn':r['mpn'],'refs':r['refs'],'assigned_code':None,'account_registration_id':None,
         'confirmed_attrition_qty':None,'supplier_quote_document':None,'real_invoice_document':None,'jlc_package_label_document':None,
         'manufacturer_origin_from_invoice':None,'actual_unit_weight_g':None,'warehouse_status':None,'usable_inventory_qty':None,
         'jlc_assembly_and_rotation_accepted':False,'externally_reviewed_by':None} for r in plan['request_lines']],
       'rtc_factory_assembly_sku':None,'rtc_factory_drawing':None,'cell_installed_height_maximum':None,'cell_assembly_accepted':False}
    (output/'SUPPLIER-REPLY-TEMPLATE-NOT-RECEIPT.json').write_text(json.dumps(template,ensure_ascii=False,indent=2)+'\n')
    instructions='''# Panda7 — technical pre-registration packet (NOT an order)

本包补全7个必需SMT位号与1个RTC后装组件的技术登记资料。没有寄料、付款、账户登记、
库存预留或对外发信。没有改动正式CAD、网络、已通过的布线与12个现有映射。

## 公开检索已恢复并复核
已使用匿名浏览器加载真实嘉立创检索，C74301阳性对照命中1项。三个SGMICRO系列
未观察到精确匹配。U22401系列找到4项，但不是目前的-17精确身份。
C49325733的U22401-23是1.6mm沉板，不能代替0.8mm版本；-38为LCP/镀金闪镀，
-05为不同材料后缀且目录归于JLCPCB Assembly；无后缀C5128294同样不能证明匹配。
这些新发现没有被填进原型号的C码栏。另一次LCSC访问被拒绝，不能据此声称无货。

## 原生封装登记
EXACT-PART-REGISTRATION.csv保留4/1/1/1的每Core用量和精确MSL、封装与原厂链接。
NATIVE-PLACEMENT-REFERENCE-NOT-MACHINE-CPL.csv直接读取当前PCB姿态；它不是贴片机的
最终旋转校正文件。NATIVE-PIN-MAP.csv保留21号TQFN裸露焊盘，不把4个钢网窗口当新引脚。
WLCSP为0.5mm/0.4mm球距；来料必须可追溯、带准确后缀和封装标记，不能仅用系列名替代。

## BT301的组件请求已绑定实际落点
内部请求编号PANDA7-RTC-CR1216-LEAD-REQUEST-A，不是已经存在的厂家SKU。
正极落点(58.5,56.4)mm接RTC_CELL_P，负极(68.5,56.4)mm接GND，均为2x2mm焊盘。
现有两焊盘位于名义电池本体下方，厂家必须确认柔性引线/绝缘片/粘贴的装配顺序，
不能用裸电池尺寸代替成品组件，更不能令未绝缘焊片压在PCB铜箔上。
2.4mm为本项目安装高度预算，不是厂家已承诺上限。不得回流或直接焊裸电池。
RTC反向充电/24h保持及温度验证仍是独立的未通过项目。

## 注册与采购所缺的真实输入
Core/Display贴装数量尚未确认；没有默认按5套/10套计算。实际损耗要按嘉立创回复填写。
真实购买发票、原产地、单价/单位重量、账户内收货指引和标签必须来自交易，不可猜测。
技术询问可以先询样品MOQ，但采购/寄料必须等待登记；数量为空的表不可提交采购。
Received/Checked仅表示收件/检查，不是In Warehouse。只有身份/文件经人工审查、
入库可用数量足够才可将这四种物料记为可用；这仍不等于整机制造放行。

本包不包含完整电路原理图或PCB铜箔，可先用于型号/工艺预登记，减少不必要的设计披露。
'''+plan['jlc_policy_url']+'\n'
    (output/'START-HERE.md').write_text(instructions)
    sg='\n'.join(f"{r['mpn']} | {r['package']} | MSL{r['moisture_sensitivity_level']} | 每Core{r['qty_per_core']}个" for r in plan['request_lines'] if r['manufacturer']=='SGMICRO')
    draft='''# 待发送技术预询问（不是采购指令）
收件渠道：SGMICRO官网sales_china@sg-micro.com或官网授权代理Sekorm。

请确认以下精确型号的样品/最小供货量、交期、原厂卷带/剪带形式和可追溯票据，
以及供应嘉立创SMT客供是否有既有精确物料登记号。项目尚未确定总贴装数量，
本次只请求技术/供料确认，不授权订单、付款、替代、发货或物料预留。
'''+sg+'''

SGM2578SD需保留QOD/反向电流相关功能，不能替换S；SGM62125A不可替换B/C/D；
SGM37601必须20脚YTRL20，不可替换24脚。请回填完整后缀/当前原厂图/包装标签与MSL，
报价可先给样品MOQ档和阶梯价，不要把每板用量理解为已确认采购量。
'''
    (output/'RFQ-SGMICRO-PREFLIGHT-UNSENT.md').write_text(draft)
    (output/'RFQ-JLC-PREFLIGHT-UNSENT.md').write_text('''# 待发送技术预登记询问（不是订单）
收件：support@jlcpcb.com。
请核对EXACT-PART-REGISTRATION.csv的4种精确原厂料和本项目的WLCSP/20脚TQFN/
0.8mm沉板USB装配能力，回填可用的目录号或客户物料登记流程、来料形式、贴装旋转及
损耗要求。总贴装数量待用户确认；未授权报价接受、采购、替代或寄料。
公开目录中的U22401-23并非0.8mm型号；C9900262011不得未经核对匹配到-17。
请先提供技术登记反馈；真实收货指引只能在客户账户登记后生成，不先行寄料。
''')
    (output/'RFQ-MUP-PREFLIGHT-UNSENT.md').write_text('''# 待发送技术预询问（不是采购指令）
收件：sales@mupconnector.com。
需求为U22401-17，NYLON/Au3u、CH0.78、0.8mm沉板、16触点、9.24mm PCB槽。
请确认当前图纸/订购后缀、MSL/包装、样品MOQ、交期，以及供嘉立创的既有精确登记号。
不把U22401-23的1.6mm沉板、U22401-38的镀金规格或目录无后缀项视为相同型号。
可另外提供-05的同尺寸LCP替代候选，但必须明确变更和可追溯料号，现阶段不授权替代。
每Core1个，总数量和嘉立创损耗待确认。不要发货或预留物料。
''')
    (output/'RFQ-BT301-PREFLIGHT-UNSENT.md').write_text('''# 待发送工厂组件图询问（不是采购指令）
收件：dqq@szlijia.com（Omnergy官网）。
请对BT301-FACTORY-DRAWING-REQUEST.json提供CR1216原厂绝缘引线组件的图纸、
厂家成品SKU/图号、极性、线径/线长/端部、固定和应力释放方案、最大外形及样品MOQ。
内部请求编号不是厂家既有SKU，2.4mm是项目安装预算，不代表已经验证的电池最大高度。
两落点在电池本体下方，请确认可安全装配的引线方案与绝缘，不允许直接焊裸电池或回流。
总套数尚未确定，不授权替代、电池生产、付款或发货。电路安全测试另行进行。
''')
    report={'schema':'panda-seven-mm-supply-preflight-v1','source_contract_sha256':sha(CONTRACT),'native':native,
        'technical_request_rows':4,'pending_smt_refs':7,'required_post_smt_refs':1,'quantities':quant,
        'registration_submitted':False,'supplier_requests_sent':False,'actual_inventory_accepted':False,
        'production_assembly_ready':False,'manufacturing_release':False}
    (output/'PREFLIGHT-NATIVE-EVIDENCE.json').write_text(json.dumps(report,indent=2)+'\n')
    files={p.name:sha(p) for p in output.iterdir() if p.is_file()}
    (output/'MANIFEST.json').write_text(json.dumps({'files':files,'output':str(output),'all_files_are_request_or_review_not_receipt':True},indent=2)+'\n')
    print(json.dumps({'output':str(output),'files':len(files),'native':{n:r['counts'] for n,r in native.items()},'codes_newly_assigned':0,'pending_smt_refs':7,'requests_sent':False},indent=2))
    return report

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--candidate',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--core-quantity',type=int);parser.add_argument('--display-quantity',type=int)
    a=parser.parse_args();export(a.candidate,a.output,a.core_quantity,a.display_quantity)
