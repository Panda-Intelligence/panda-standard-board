import sys, json
import pcbnew

def mm(val):
    return pcbnew.FromMM(val)

def pcb_point(x, y):
    return pcbnew.VECTOR2I(mm(x), mm(y))

def run(src_path, dst_path):
    print(f"Loading board: {src_path}")
    b = pcbnew.LoadBoard(src_path)
    
    nets = {
        'GND': b.FindNet('GND'),
        'P47_D0': b.FindNet('P47_D0'),
        'P47_XSTL': b.FindNet('P47_XSTL'),
        'P47_CKV': b.FindNet('P47_CKV'),
        'P47_SPV': b.FindNet('P47_SPV'),
        'VSYS_RAW': b.FindNet('VSYS_RAW'),
        '3V3_AON': b.FindNet('3V3_AON'),
        '3V3_EPD_LOGIC': b.FindNet('3V3_EPD_LOGIC'),
        'EXP_INT': b.FindNet('EXP_INT'),
        'I2C_SDA': b.FindNet('I2C_SDA'),
        'P47_PGOOD': b.FindNet('P47_PGOOD'),
        'I2C_SCL': b.FindNet('I2C_SCL'),
        'HW_ARM_GPIO': b.FindNet('HW_ARM_GPIO'),
    }
    
    # 1. Obsolete stubs and dead segments to delete by exact UUID
    stubs_to_delete = {
        # GND dead stubs
        '0961e34a-799b-5902-8835-dc3348f8cf60',
        '62fafed7-dccc-5aff-989e-9256f854f1c6',
        
        # P47_XSTL obsolete detours and dead stub
        'da90da9a-ac89-47c0-a667-755bca5a0ab9',
        '70126a5d-4025-424b-adb3-0faec8a3d06f',
        '74903065-37c7-454a-8ddb-53a64d463a1a',
        'b130770f-9fc7-44f0-9a53-6019f1fc4960', # Dangling F.Cu stub at (33.2363, 106.4002)
        
        # VSYS_RAW pin 15/16 dead stubs and obsolete F.Cu detour
        '6ba56b05-23a8-4224-9fbe-27e9907329a5',
        '75f0708a-170f-49d7-b0bb-197fb39155c7',
        'a433c72e-e6b9-41b0-81d1-eded2661524a',
        'da124922-9ac3-4d62-9760-4913954a0609',
        'fa74b9e1-170b-586d-8cc6-052e47faf5c4',
        'bf3274d5-14eb-5ddb-a0cc-03ee640d78aa',
        'c2289131-85ea-5edf-9496-b28162712667',
        '3a85a6f2-55f3-5e1d-be8f-55323f1d8dc8',
        'f2f16061-d4b6-5454-9240-9acd7ff51c9c',
        'a577b048-6a37-4d42-b007-bec4f7ddc7dc',
        '35058442-2eb4-443f-802c-9fc66f5ef50b',
        'a9c436be-fc45-4856-9847-b228233012ff',
        '845fb8a1-46ef-4c98-a504-fe8039d19dff',
        'f550fdcd-2d4e-4849-9688-108f57955603',
        '4198eb80-a7cf-4e22-95e2-e1ec0c700a91',
        'c13a2a65-08d9-4f3f-8078-5ce846fad590',
        '37a578ae-af6d-4854-9363-cfdb09fb4068',
        '2bccca1e-e2fa-4709-8a69-c43ea2309b44',
        '3548f11c-a619-4161-85de-bcdef5f5e067',
        
        # 3V3_AON obsolete stubs and old detour
        '66000406-69af-43c2-973a-57ee787e9487',
        '921861f9-68a8-4fb2-84a3-d770c367c791',
        '40e2125c-49ff-4fde-9b2d-7d2691cd409c',
        'd10c2566-f2db-419e-b0d0-60e16c13e74f',
        '35398bae-d6ea-437e-b80c-ea540e117b41',
        '5c25d9b2-07c7-44d3-9c1e-64cedd51c38f',
        'd91db2b7-e47d-4311-b05f-d7b20306a773',
        '8e8f91b7-ba40-4333-b446-64b3c3c78641',
        'eac82824-0939-5d70-9a93-5b0b8930cfc6',
        '37258dfa-f13e-593d-b628-9ffc400a3b58',
        '30bc46f2-9af0-531b-9de0-8c15c17249fd',
        'b6e4ee06-e089-5d14-9189-c3f8c9bf0848',
        
        # 3V3_EPD_LOGIC connector pad stubs and dead segments
        '366c1a81-6d79-4240-85a8-86288db5121e',
        '6ae9569e-3682-5d09-bdd8-6808721af4b6',
        '505f2d48-cc86-5b73-b080-ce3827c62b2f',
        '0e45cbe2-b843-55cb-9ddd-78109957fa37',
        'e7364949-da0c-59e3-9758-9af57f3d597e',
        '0436cc71-a15f-5e9e-9b0c-588ca29b8de7',
        '6aaa45da-c8c8-5dd4-aaaa-6bd9f7f5fbbc', # Dead stub to removed J1 pin 13
        
        # EXP_INT dead connector stubs
        '67b3f365-04b3-4afe-b829-9b359030a85a',
        '10c6ccaf-63b4-4207-a436-e7b86e7f83fe',
        '69da9b52-d2f1-5022-8b41-1efade4af387',
        
        # HW_ARM_GPIO dead connector stubs
        '9756bbab-96be-479f-80fa-9834dfb5ca87',
        '0fd6b1b1-0d91-57e9-bbcf-61abce3c0496',
        
        # I2C_SCL dead connector stubs
        'cb7df3f5-6f72-4fde-ba63-45ef859c148c',
        '462e2cee-5f2e-49a9-a626-2d2694d38015',
        '93814519-c4c3-5344-b874-9d6106671401',
        'f79be175-559d-53bf-820a-4c687f54fb34',
        '0dc544ef-6b1a-5724-a261-f7f305ee6587', # Dead stub at (43.9, 115.45)
        '2ef6974c-c7bd-5d62-8e6e-c20763f45f17', # Dead stub at (43.75, 115.45) -> (43.4, 115.8)
        '839b46a1-f910-4a6f-942b-65c2301b63aa', # Dead stub at (34.0203, 115.4002)
        
        # I2C_SDA dead connector stubs
        '7819160a-f405-4ac9-ad9a-c112d7d34b08',
        'a39253ec-91e1-4cf2-925c-a6902b129292',
        'abb125e8-f744-4845-a2d8-305622ec0f3c',
        'c512f3d8-08ea-44de-8785-ddd939a59191',
        'b655e106-9292-4870-b1b3-80f8c3a534af',
        
        # P47_PGOOD dead connector stubs, dangling via and dead stub
        'f70257ea-00a6-4e49-b2b5-97c94aaf7c60',
        '0345eb4e-71f3-4cdf-bae1-bd96d43e23d6',
        'fa86e037-bf67-4783-956f-e230a182de50',
        'c39c0ef3-a09f-413c-81cb-ce0f82321b82',
        '58c258c0-b2bd-4e92-83e4-3cf39bebdc10',
        '8967b42b-0e5c-4f40-8258-4b4bfab96ff3', # Dangling via at (44.1, 117.05)
        '5e35ece6-0de0-4be3-9cff-1c3326f1dc80', # Dangling track on In2.Cu from (43.65, 116.6) to (44.1, 117.05)
        
        # P47_CKV Core obsolete escape tracks
        '5fa0d70c-3fac-4e7d-987f-98a52f495496',
        '3a631b53-d232-453c-b6d1-6f44fe803cec',
        '2768d0da-798b-4cbd-99a6-1c18055b1927',
        '3ebd6d9f-5c57-405d-b400-1d8e697f7c6f',
        '743c660d-5265-4970-9e5e-3c5c89d53e3d',
    }
    
    tracks_to_delete = []
    for t in b.GetTracks():
        if t.m_Uuid.AsString() in stubs_to_delete:
            tracks_to_delete.append(t)
            
    print(f"Deleting {len(tracks_to_delete)} verified dead stubs/vias...")
    for t in tracks_to_delete:
        b.Delete(t)

    def add_track(net, layer, p1, p2, width_mm=0.15):
        t = pcbnew.PCB_TRACK(b)
        t.SetNet(net)
        t.SetLayer(layer)
        t.SetStart(pcb_point(p1[0], p1[1]))
        t.SetEnd(pcb_point(p2[0], p2[1]))
        t.SetWidth(mm(width_mm))
        b.Add(t)
        return t

    def add_via(net, pos, drill_mm=0.20, size_mm=0.45):
        v = pcbnew.PCB_VIA(b)
        v.SetNet(net)
        v.SetPosition(pcb_point(pos[0], pos[1]))
        v.SetDrill(mm(drill_mm))
        v.SetWidth(mm(size_mm))
        v.SetViaType(pcbnew.VIATYPE_THROUGH)
        b.Add(v)
        return v

    # 2. P47_D0 Display tracks/vias from Display.kicad_pcb
    disp_b = pcbnew.LoadBoard('.work/single_pcb_clean/Display.kicad_pcb')
    d0_net = nets['P47_D0']
    for t in disp_b.GetTracks():
        if t.GetNetname() == 'P47_D0':
            if isinstance(t, pcbnew.PCB_VIA):
                pos = (pcbnew.ToMM(t.GetPosition().x), pcbnew.ToMM(t.GetPosition().y))
                if pos[0] < 32.5:
                    v = pcbnew.PCB_VIA(b)
                    v.SetNet(d0_net)
                    v.SetPosition(t.GetPosition())
                    v.SetDrill(t.GetDrill())
                    v.SetWidth(t.GetWidth())
                    v.SetViaType(t.GetViaType())
                    b.Add(v)
            else:
                p1 = (pcbnew.ToMM(t.GetStart().x), pcbnew.ToMM(t.GetStart().y))
                p2 = (pcbnew.ToMM(t.GetEnd().x), pcbnew.ToMM(t.GetEnd().y))
                if p1[0] < 32.8 and p2[0] < 32.8:
                    tr = pcbnew.PCB_TRACK(b)
                    tr.SetNet(d0_net)
                    tr.SetLayer(t.GetLayer())
                    tr.SetStart(t.GetStart())
                    tr.SetEnd(t.GetEnd())
                    tr.SetWidth(t.GetWidth())
                    b.Add(tr)
    print("Restored P47_D0 Display tracks/vias.")

    # 3. P47_CKV
    # Run along Y=104.95 on F.Cu to X=38.8.
    # Hop under SPV (Y=105.95) on In2.Cu from (38.8, 104.95) to (38.8, 106.95).
    # Return to F.Cu at (38.8, 106.95), run along Y=106.95 to X=42.2, then (42.475, 106.475) to Core via (44.375, 106.475).
    # Since CKV enters VIA P47_CKV on F.Cu and Core exits on B.Cu, VIA P47_CKV is fully connected!
    add_track(nets['P47_CKV'], pcbnew.F_Cu, (32.7, 105.45), (33.2, 104.95), 0.15)
    add_track(nets['P47_CKV'], pcbnew.F_Cu, (33.2, 104.95), (38.8, 104.95), 0.15)
    add_via(nets['P47_CKV'], (38.8, 104.95), 0.20, 0.40)
    add_track(nets['P47_CKV'], pcbnew.In2_Cu, (38.8, 104.95), (38.8, 106.95), 0.15)
    add_via(nets['P47_CKV'], (38.8, 106.95), 0.20, 0.40)
    add_track(nets['P47_CKV'], pcbnew.F_Cu, (38.8, 106.95), (42.2, 106.95), 0.15)
    add_track(nets['P47_CKV'], pcbnew.F_Cu, (42.2, 106.95), (42.475, 106.475), 0.15)
    add_track(nets['P47_CKV'], pcbnew.F_Cu, (42.475, 106.475), (44.375, 106.475), 0.15)

    # 4. P47_SPV
    # Connect directly from Display (32.7, 105.95) across to Core escape route at (44.655229, 105.95) on F.Cu.
    # Jog north around Via 3V3_EPD_LOGIC at (42.0, 106.05) to Y=105.35.
    add_track(nets['P47_SPV'], pcbnew.F_Cu, (32.7, 105.95), (41.2, 105.95), 0.15)
    add_track(nets['P47_SPV'], pcbnew.F_Cu, (41.2, 105.95), (41.8, 105.35), 0.15)
    add_track(nets['P47_SPV'], pcbnew.F_Cu, (41.8, 105.35), (42.2, 105.35), 0.15)
    add_track(nets['P47_SPV'], pcbnew.F_Cu, (42.2, 105.35), (42.8, 105.95), 0.15)
    add_track(nets['P47_SPV'], pcbnew.F_Cu, (42.8, 105.95), (44.655229, 105.95), 0.15)

    # 5. P47_XSTL
    # From Display trace ending at (33.01, 106.40)
    add_track(nets['P47_XSTL'], pcbnew.F_Cu, (33.01, 106.40), (37.0, 106.40), 0.15)
    add_via(nets['P47_XSTL'], (37.0, 106.40), 0.20, 0.45)
    add_track(nets['P47_XSTL'], pcbnew.B_Cu, (37.0, 106.40), (37.0, 104.45), 0.15)
    add_via(nets['P47_XSTL'], (37.0, 104.45), 0.20, 0.45)
    add_track(nets['P47_XSTL'], pcbnew.F_Cu, (37.0, 104.45), (44.655229, 104.45), 0.15)

    # 6. VSYS_RAW
    # Connect Display B.Cu trace directly to via (34.65, 110.35)
    add_track(nets['VSYS_RAW'], pcbnew.B_Cu, (34.75, 110.05), (34.65, 110.35), 0.35)
    # Bridge via (34.65, 110.35) on F.Cu to Core via (44.125, 109.825)
    add_track(nets['VSYS_RAW'], pcbnew.F_Cu, (34.65, 110.35), (35.175, 109.825), 0.35)
    add_track(nets['VSYS_RAW'], pcbnew.F_Cu, (35.175, 109.825), (44.125, 109.825), 0.35)

    # 7. 3V3_AON
    # F.Cu track from Display via (34.675, 111.9) to Core PMIC pad (45.1, 111.825)
    add_track(nets['3V3_AON'], pcbnew.F_Cu, (34.675, 111.9), (34.75, 111.825), 0.35)
    add_track(nets['3V3_AON'], pcbnew.F_Cu, (34.75, 111.825), (45.1, 111.825), 0.35)
    # Feed Display U811 on In2.Cu from via (34.675, 111.9)
    add_track(nets['3V3_AON'], pcbnew.In2_Cu, (34.675, 111.9), (35.116, 111.9), 0.25)
    add_track(nets['3V3_AON'], pcbnew.In2_Cu, (35.116, 111.9), (35.116, 114.225), 0.25)
    add_via(nets['3V3_AON'], (35.116, 114.225), 0.20, 0.45)

    # 8. 3V3_EPD_LOGIC
    # Connect Display trace to Y=112.90 and across to Core via 4e2a8317 at (44.125, 113.35)
    add_track(nets['3V3_EPD_LOGIC'], pcbnew.F_Cu, (32.073, 113.45), (32.7, 113.45), 0.15)
    add_track(nets['3V3_EPD_LOGIC'], pcbnew.F_Cu, (32.7, 113.45), (33.15, 112.90), 0.15)
    add_track(nets['3V3_EPD_LOGIC'], pcbnew.F_Cu, (33.15, 112.90), (43.675, 112.90), 0.15)
    add_track(nets['3V3_EPD_LOGIC'], pcbnew.F_Cu, (43.675, 112.90), (44.125, 113.35), 0.15)

    # 9. EXP_INT
    # Direct In2.Cu bridge from Display via (34.5133, 116.5704) to Core via 006913ae at (43.200, 115.150)
    add_track(nets['EXP_INT'], pcbnew.In2_Cu, (34.5133, 116.5704), (35.9333, 115.1500), 0.15)
    add_track(nets['EXP_INT'], pcbnew.In2_Cu, (35.9333, 115.1500), (43.2000, 115.1500), 0.15)
    # Bridge Core pad gap (44.575, 116.4) to (45.75, 116.45) on F.Cu
    add_track(nets['EXP_INT'], pcbnew.F_Cu, (44.575, 116.4), (45.75, 116.45), 0.15)

    # 10. HW_ARM_GPIO
    # Route on B.Cu dipping to Y=115.95 (giving >0.32mm clearance to Via EXP_INT at Y=116.5704 and >0.24mm to Via I2C_SCL at Y=115.4002)
    add_track(nets['HW_ARM_GPIO'], pcbnew.B_Cu, (31.683, 116.95), (32.833, 115.95), 0.15)
    add_track(nets['HW_ARM_GPIO'], pcbnew.B_Cu, (32.833, 115.95), (35.500, 115.95), 0.15)
    add_track(nets['HW_ARM_GPIO'], pcbnew.B_Cu, (35.500, 115.95), (36.500, 116.95), 0.15)
    add_track(nets['HW_ARM_GPIO'], pcbnew.B_Cu, (36.500, 116.95), (45.475, 116.95), 0.15)

    # 11. P47_PGOOD
    # Connect from Display trace (31.404, 117.553) to In2.Cu via at (34.0, 117.8)
    add_track(nets['P47_PGOOD'], pcbnew.F_Cu, (31.404, 117.553), (31.971, 117.553), 0.15)
    add_track(nets['P47_PGOOD'], pcbnew.F_Cu, (31.971, 117.553), (32.073, 117.45), 0.15)
    add_track(nets['P47_PGOOD'], pcbnew.F_Cu, (32.073, 117.45), (33.65, 117.45), 0.15)
    add_track(nets['P47_PGOOD'], pcbnew.F_Cu, (33.65, 117.45), (34.0, 117.8), 0.15)
    add_via(nets['P47_PGOOD'], (34.0, 117.8), 0.20, 0.45)
    add_track(nets['P47_PGOOD'], pcbnew.In2_Cu, (34.0, 117.8), (34.6, 117.2), 0.15)
    add_track(nets['P47_PGOOD'], pcbnew.In2_Cu, (34.6, 117.2), (35.4, 117.2), 0.15)
    add_track(nets['P47_PGOOD'], pcbnew.In2_Cu, (35.4, 117.2), (36.0, 116.6), 0.15)
    add_track(nets['P47_PGOOD'], pcbnew.In2_Cu, (36.0, 116.6), (43.65, 116.6), 0.15)

    # 12. I2C_SDA
    # F.Cu track from Display (30.663, 116.284) to via at (31.046, 115.9)
    # Then B.Cu track along Y=113.35 across to Core via at (43.2, 113.8)
    add_via(nets['I2C_SDA'], (31.046, 115.9), 0.20, 0.45)
    add_track(nets['I2C_SDA'], pcbnew.B_Cu, (31.046, 115.9), (32.796, 114.15), 0.15)
    add_track(nets['I2C_SDA'], pcbnew.B_Cu, (32.796, 114.15), (34.200, 114.15), 0.15)
    add_track(nets['I2C_SDA'], pcbnew.B_Cu, (34.200, 114.15), (35.000, 113.35), 0.15)
    add_track(nets['I2C_SDA'], pcbnew.B_Cu, (35.000, 113.35), (42.750, 113.35), 0.15)
    add_track(nets['I2C_SDA'], pcbnew.B_Cu, (42.750, 113.35), (43.200, 113.80), 0.15)

    # 13. I2C_SCL
    # Display via at (34.0203, 115.4002) is preserved.
    # Hop under 3V3_AON (which is at X=35.1156 on F.Cu) on B.Cu:
    # Run along Y=115.4002 to X=35.60 (clear of 3V3_AON via which is at (35.116, 114.225) by >0.87mm).
    # Then jog diagonally to (36.50, 114.50) -> (36.80, 114.50).
    # Via up to F.Cu at (36.80, 114.50) (size 0.40, drill 0.20).
    # Then on F.Cu: (36.80, 114.50) -> (38.10, 115.80) -> (43.40, 115.80) to Core trace!
    add_track(nets['I2C_SCL'], pcbnew.B_Cu, (34.0203, 115.4002), (35.6000, 115.4002), 0.15)
    add_track(nets['I2C_SCL'], pcbnew.B_Cu, (35.6000, 115.4002), (36.5000, 114.5000), 0.15)
    add_track(nets['I2C_SCL'], pcbnew.B_Cu, (36.5000, 114.5000), (36.8000, 114.5000), 0.15)
    add_via(nets['I2C_SCL'], (36.8000, 114.5000), 0.20, 0.40)
    add_track(nets['I2C_SCL'], pcbnew.F_Cu, (36.8000, 114.5000), (38.1000, 115.8000), 0.15)
    add_track(nets['I2C_SCL'], pcbnew.F_Cu, (38.1000, 115.8000), (43.4000, 115.8000), 0.15)

    print("All routes and connections added successfully.")
    
    pcbnew.SaveBoard(dst_path, b)
    print(f"Board saved to {dst_path}")
    return True

if __name__ == '__main__':
    src = sys.argv[1] if len(sys.argv) > 1 else '.work/single_pcb_clean/Single_step1.kicad_pcb'
    dst = sys.argv[2] if len(sys.argv) > 2 else '.work/single_pcb_clean/Single.kicad_pcb'
    run(src, dst)
