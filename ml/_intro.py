import inspect
from ai_edge_quantizer import quantizer, recipe
print("Quantizer.__init__:", inspect.signature(quantizer.Quantizer.__init__))
print("load_quantization_recipe:", inspect.signature(quantizer.Quantizer.load_quantization_recipe))
print("calibrate:", inspect.signature(quantizer.Quantizer.calibrate))
print("quantize:", inspect.signature(quantizer.Quantizer.quantize))
print("static_wi8_ai8:", inspect.signature(recipe.static_wi8_ai8))
try:
    from ai_edge_quantizer import qtyping
    print("qtyping ok")
except Exception as e:
    print("qtyping:", e)
