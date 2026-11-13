-- CI's dummy layer: a "place" layer from place=* nodes. Not an example
-- to copy for a real layer.

function node_function()
  local place = Find("place")
  if place ~= "" then
    Layer("place", false)
    Attribute("class", place)
    Attribute("name", Find("name"))
  end
end

function way_function()
  -- no way-derived layers in this dummy profile
end
