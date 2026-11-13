node_keys = { "amenity" }

function node_function()
  if Find("amenity") == "waste_basket" then
    Layer("bins", false)
  end
end

function way_function()
end
