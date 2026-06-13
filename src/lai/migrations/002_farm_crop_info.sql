-- Metadados da cultura/fazenda para o LAI saber o que é a lavoura.
-- (crop_name, variedade, localização, coords, início da safra)

ALTER TABLE farm_owners ADD COLUMN IF NOT EXISTS crop_name     text;
ALTER TABLE farm_owners ADD COLUMN IF NOT EXISTS crop_variety  text;
ALTER TABLE farm_owners ADD COLUMN IF NOT EXISTS location_name text;
ALTER TABLE farm_owners ADD COLUMN IF NOT EXISTS latitude      double precision;
ALTER TABLE farm_owners ADD COLUMN IF NOT EXISTS longitude     double precision;
ALTER TABLE farm_owners ADD COLUMN IF NOT EXISTS season_start  date;

-- Seed: farm-001 (de crop-gym/scripts/run_farm.py + potato_cropcalendar.yaml).
UPDATE farm_owners SET
    crop_name     = 'batata',
    crop_variety  = 'Potato_701',
    location_name = 'Suzano, SP — Brasil',
    latitude      = -23.54,
    longitude     = -46.32,
    season_start  = '2006-01-01'
WHERE farm_id = 'farm-001';
