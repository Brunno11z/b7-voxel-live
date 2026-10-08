from configuration import Settings
from game.presentation import action_description,gift_caption
from game.voxel_character import VoxelCharacter

def test_gift_guide_uses_actual_binding_and_configured_quantity():
 cfg=Settings(mappings=[{'gift_id':'123','gift_name':'Rosa','action':'BUILD'}])
 assert action_description('BUILD',cfg.amounts['BUILD'])=='Constrói 8 blocos'
 assert action_description('TNT',8)=='Destrói 8 blocos'
 assert action_description('WIN',1)=='Ganha 1 vitória'
 assert action_description('LOSE',3)=='Perde 3 vitórias'
 assert gift_caption('BUILD',cfg,{'123':{'icon':'https://example.org/rose.png'}})==('Rosa','https://example.org/rose.png')
 assert gift_caption('TNT',cfg,{})==('Sem presente vinculado','')

def test_cuboid_character_has_distinct_articulated_poses():
 import pygame as pg
 pg.init();pg.display.set_mode((1,1));c=VoxelCharacter()
 poses=[c.frame(s,3) for s in ['idle','walk','jump','build','celebrate']]
 pixels=[pg.image.tobytes(s,'RGBA') for s in poses]
 assert len(set(pixels))==5
 assert all(s.get_bounding_rect().height>80 for s in poses)
 assert c.frame('walk',3) is poses[1]
 assert pg.image.tobytes(c.frame('walk',3,-1),'RGBA')!=pixels[1]
 pg.quit()
