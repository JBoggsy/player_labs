' unit C.idle sha256:10c9eb9134b824a7d7cea1f76f6ec2a5ab9179d38e9f8153dfa129009df1f406 generated, do not edit
SUB c_idle__start()
  c_idle__observed_x = k_position__x
  c_idle__status = 0
END SUB

SUB c_idle__tick()
  c_idle__observed_x = k_position__x
  c_idle__status = 0
END SUB
