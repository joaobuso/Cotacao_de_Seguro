# parser_validacao.py
import re

OBRIGATORIOS = ["cep","rua","numero","bairro","uf","cidade","valor","nome","cpf"]

MAPA_CAMPOS = {
    "nome_solicitante":"nome",
    "cpf_solicitante":"cpf",
    "estado":"uf",
    "endereco":"rua",  # se vier rua completa
}

def somente_digitos(s: str) -> str:
    return re.sub(r"\D", "", s or "")

def normaliza_valor(v: str) -> str:
    if not v: return ""
    v = v.strip().replace(".", "").replace("R$", "").replace(" ", "")
    v = v.replace(",", ".")
    return v  # deixe como string decimal, ex: "10000.00" se quiser

def normaliza_e_valida(dados: dict) -> tuple[dict, list]:
    # 1) aplica renomeação de chaves
    dados2 = {}
    for k, v in (dados or {}).items():
        k2 = MAPA_CAMPOS.get(k, k)
        dados2[k2] = v

    # 2) normalizações
    dados2["cep"]   = somente_digitos(dados2.get("cep"))
    dados2["cpf"]   = somente_digitos(dados2.get("cpf"))
    dados2["uf"]    = (dados2.get("uf") or "").strip().upper()
    dados2["valor"] = normaliza_valor(dados2.get("valor") or dados2.get("valor_animal"))

    # 3) faltantes
    faltantes = [c for c in OBRIGATORIOS if not (dados2.get(c) or "").strip()]

    # 4) flag
    dados2["dados_completos"] = (len(faltantes) == 0)
    return dados2, faltantes
