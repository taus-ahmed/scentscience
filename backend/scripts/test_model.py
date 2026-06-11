import sys
sys.path.insert(0, '.')

from ml.model import train_all_models, load_models, predict
import json

with open('data/seed_perfumes.json') as f:
    perfumes = json.load(f)

print(f'Training on {len(perfumes)} perfumes...')
train_all_models(perfumes)

models = load_models()
print(f'Models loaded: {list(models.keys())}')

sauvage = next(p for p in perfumes if p['name'] == 'Sauvage' and p['brand'] == 'Dior' and p['concentration'] == 'EDT')
result = predict(sauvage, models)

print(f"Longevity: {result['longevity_hours']:.1f}h")
print(f"Sillage: {result['sillage_score']:.1f}/10")
print(f"Blind buy: {result['blind_buy_score']:.1f}/10")
print(f"Versatility: {result['versatility_score']:.1f}/10")
print(f"Season summer: {result['season_summer']:.1f}/10")
print(f"Dry down: {result['dry_down_character']}")
print("Model training SUCCESS")
