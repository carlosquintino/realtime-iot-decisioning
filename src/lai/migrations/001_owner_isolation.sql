-- Isolamento por usuário do chat LAI.
-- Cada decisão é carimbada com o dono (owner_user_id); o LAI só retorna as do
-- usuário logado. Mapeamento fazenda->dono em farm_owners.

ALTER TABLE ai_decisions ADD COLUMN IF NOT EXISTS owner_user_id text;
CREATE INDEX IF NOT EXISTS idx_ai_decisions_owner ON ai_decisions (owner_user_id, data_date DESC);

CREATE TABLE IF NOT EXISTS farm_owners (
    farm_id       text PRIMARY KEY,
    owner_user_id text NOT NULL,
    domain_id     uuid,
    created_at    timestamptz NOT NULL DEFAULT now()
);

-- Seed: farm-001 pertence ao admin (ajustar/expandir conforme novos usuários).
INSERT INTO farm_owners (farm_id, owner_user_id, domain_id)
VALUES ('farm-001', '541dcd85-0bf7-4557-8838-67f57a69e7b6', 'bfcec7dc-8a4e-4914-9641-4f8a09216067')
ON CONFLICT (farm_id) DO NOTHING;
