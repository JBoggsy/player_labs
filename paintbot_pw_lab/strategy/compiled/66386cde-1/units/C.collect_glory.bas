' unit C.collect_glory sha256:a8adf41c2dcb1f1f7ebef88db4a34e4a63e48345d0644ba44400572622846cb7 generated, do not edit
sub c_collect_glory__start()
end sub

sub c_collect_glory__tick()
  sk_motor__collect_glory(k_nearby_glory__goal_x, k_nearby_glory__goal_y)
  c_collect_glory__status = 0
end sub
