"""Classificacao de eventos coletados: triagem, area, curso, UF, nivel."""
import re
import unicodedata

UF_NOMES = {
    "AC": "Acre", "AL": "Alagoas", "AP": "Amapa", "AM": "Amazonas", "BA": "Bahia",
    "CE": "Ceara", "DF": "Distrito Federal", "ES": "Espirito Santo", "GO": "Goias",
    "MA": "Maranhao", "MT": "Mato Grosso", "MS": "Mato Grosso do Sul",
    "MG": "Minas Gerais", "PA": "Para", "PB": "Paraiba", "PR": "Parana",
    "PE": "Pernambuco", "PI": "Piaui", "RJ": "Rio de Janeiro", "RN": "Rio Grande do Norte",
    "RS": "Rio Grande do Sul", "RO": "Rondonia", "RR": "Roraima", "SC": "Santa Catarina",
    "SP": "Sao Paulo", "SE": "Sergipe", "TO": "Tocantins",
}

AREAS = {
    "Judiciária": [r"tribunal de justica", r"\btj\b", r"justica federal", r"\btrf\b", r"analista judiciario", r"tecnico judiciario", r"\btrt\b", r"justica do trabalho", r"\btre\b", r"justica eleitoral", r"tribunal regional"],
    "Ministério Público/Defensoria": [r"ministerio publico", r"\bmp\b", r"\bmpe\b", r"\bmpf\b", r"promot", r"defensoria", r"\bdpe\b", r"defensor publico"],
    "Policial/Bombeiro": [r"policia", r"delegado", r"escrivao", r"investigador", r"papiloscop", r"perito criminal", r"guarda municipal", r"bombeiro", r"agente de seguranca", r"carcerario", r"policial", r"\bpm\b", r"\bprf\b", r"rodoviaria"],
    "Saúde": [r"medic[oa]", r"enferm", r"farmac", r"odont", r"dentista", r"psicolog", r"nutri", r"fisioterap", r"fono", r"biomedic", r"saude", r"veterinar", r"biologo", r"agente comunitario", r"tecnicos? em enfermagem", r"fonoaudiolog"],
    "Educação": [r"professor", r"docente", r"magisterio", r"pedagog", r"educacao", r"inspetor escolar", r"creche", r"seduc"],
    "Tecnologia da Informação": [r"tecnologia da informacao", r"\bti\b", r"analista de sistemas?", r"desenvolvedor", r"programador", r"informatica", r"suporte tecnico", r"banco de dados", r"ciencia da computacao", r"tecnico em informatica"],
    "Engenharia/Arquitetura": [r"engenheir", r"arquitet", r"agronomo", r"agronomia", r"florestal", r"geologo", r"topograf", r"mensurador", r"geoprocessamento"],
    "Fiscal/Auditoria": [r"fiscal", r"auditor", r"tributario", r"tributacao", r"receita"],
    "Jurídica": [r"advogad", r"juridic", r"consultor juridico", r"procurador", r"assessor juridico", r"assessoria juridica"],
    "Economia/Contabilidade": [r"contad", r"contabil", r"economi", r"financ", r"bancari", r"\bcaixa\b", r"economista"],
    "Agropecuária": [r"agricol", r"agropecuar", r"zootecn", r"pecuaria", r"tecnico agricola"],
    "Comunicação": [r"jornalist", r"publicidade", r"comunicacao social", r"radialista", r"designer"],
    "Social": [r"servico social", r"assistente social", r"sociolog", r"antropolog", r"cultural", r"esporte", r"educacao fisica"],
    "Administrativa": [r"administrativ", r"auxiliar", r"assistente", r"escriturario", r"atendente", r"secretar", r"almoxarif", r"compras", r"licita", r"recursos humanos", r"porteiro", r"motorista", r"almoxarifado", r"gestao"],
}

CURSOS = {
    "Direito": [r"direito", r"bacharel em direito"],    "Medicina": [r"medicina", r"\bmedic[oa]\b"],
    "Enfermagem": [r"enfermagem", r"enfermeir"],
    "Farmácia": [r"farmaci", r"farmaceutic"],
    "Odontologia": [r"odontolog", r"cirurgiao-dentista", r"dentista"],
    "Psicologia": [r"psicolog"],
    "Fisioterapia": [r"fisioterap"],
    "Fonoaudiologia": [r"fonoaudiol"],
    "Nutrição": [r"nutricion", r"nutricao"],
    "Educação Física": [r"educacao fisica", r"\bleditor\b"],
    "Biomedicina": [r"biomedic"],
    "Medicina Veterinária": [r"veterinar"],
    "Contabilidade": [r"ciencias contabeis", r"contabeis", r"contad"],
    "Administração": [r"administracao", r"administrador"],
    "Economia": [r"ciencias economicas", r"economi"],
    "Engenharia Civil": [r"engenharia civil", r"engenheiro civil"],
    "Engenharia Elétrica": [r"engenharia eletrica", r"engenheiro eletricista"],
    "Engenharia Mecânica": [r"engenharia mecanica", r"engenheiro mecanico"],
    "Engenharia de Produção": [r"engenharia de producao"],
    "Engenharia Ambiental": [r"engenharia ambiental", r"engenheiro ambiental"],
    "Engenharia Agronômica": [r"engenharia agronomica", r"agronomia", r"agronomo"],
    "Engenharia Química": [r"engenharia quimica"],
    "Engenharia Florestal": [r"engenharia florestal"],
    "Computação/TI": [r"ciencia da computacao", r"sistemas de informacao", r"analise de sistemas", r"desenvolvimento de sistemas", r"processamento de dados", r"tecnologia da informacao", r"informatica", r"computacao", r"\bti\b"],
    "Arquitetura": [r"arquitetura", r"arquiteto"],
    "Pedagogia": [r"pedagogia", r"pedagog"],
    "Letras": [r"letras", r"portugues", r"ingles", r"espanhol"],
    "Matemática": [r"matematica", r"matematic"],
    "Física": [r"fisica"],
    "Química": [r"quimica", r"quimic"],
    "Biologia": [r"ciencias biologic", r"biologo", r"biologia"],
    "História": [r"historia"],
    "Geografia": [r"geografia", r"geograf"],
    "Serviço Social": [r"servico social", r"assistente social"],
    "Estatística": [r"estatistic"],
    "Comunicação Social": [r"comunicacao social", r"publicidade", r"jornalismo", r"relacoes publicas"],
    "Biblioteconomia": [r"biblioteconomia", r"bibliotecari"],
    "Secretariado": [r"secretariado"],
    "Turismo": [r"turismo"],
}


def normalizar(texto: str) -> str:
    t = unicodedata.normalize("NFKD", texto or "")
    t = "".join(c for c in t if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", t).lower().strip()


# "Pará" normalizado vira "para" (stopword), então exige contexto próprio
UF_PADROES = {uf: rf"\b{normalizar(nome)}\b" for uf, nome in UF_NOMES.items() if uf != "PA"}
UF_PADROES["PA"] = r"\bdo para\b|\bno para\b|\bestado do para\b|\bbelem\b|\bpara\s*[-–—:]"


def detectar_uf(texto: str):
    if not texto:
        return None
    m = re.search(r"\b(?:TJ|TRT|TRF|TRE|TCE|MPE|DPE|PM|CBM|CGM|IF)[\s\-]+([A-Z]{2})\b", texto.upper())
    if m and m.group(1) in UF_NOMES:
        return m.group(1)
    t = normalizar(texto)
    for uf, padrao in UF_PADROES.items():
        if re.search(padrao, t):
            return uf
    return None


def detectar_nivel(texto: str):
    t = normalizar(texto)
    if re.search(r"prefeitura|camara municipal|guarda municipal|municipio de", t):
        return "municipal"
    if re.search(r"\bdo estado\b|governo do estado|assembleia legislativa|tribunal de justica|secretaria de estado|policia militar|policia civil|corpo de bombeiros|\bpm\b|\bpmesp\b|\bpmmg\b|\bpmba\b", t):
        return "estadual"
    if re.search(r"\bda uniao\b|\bfederal\b|regional do trabalho|regional federal|tribunal superior|ministerio publico da uniao|policia federal|rodoviaria federal|\bprf\b", t):
        return "federal"
    return None


NEGATIVOS = (
    r"resultado final", r"homologa", r"gabarito", r"convocacao", r"nomeacao",
    r"\bposse\b", r"lista de aprovados", r"convocados?", r"reclassifica",
    r"resultado preliminar", r"edital de resultado", r"avaliacao psicologica",
    r"pericia medica", r"transferencia de local", r"desclassifica",
)

OBRIGATORIOS = (
    r"concurso", r"selecao publica", r"processo seletivo", r"seletivo simplificado",
    r"edital de abertura", r"certame",
)

PADRAO_ABERTAS = (
    r"inscricoes? abertas", r"periodo de inscricao", r"prazo de inscricao",
    r"inscricoes? ate", r"inscricoes?:\s*\d{2}/\d{2}/\d{4}",
    r"inscricoes? de \d{2}/\d{2}/\d{4}",
)


def triagem(texto: str, padrao: str = "edital_publicado"):
    """Retorna (e_concurso, status). 'padrao' e o status assumido quando o
    texto nao traz sinal explicito (ex.: listagens de banca)."""
    t = normalizar(texto)
    for p in NEGATIVOS:
        if re.search(p, t):
            return False, None
    if not any(re.search(p, t) for p in OBRIGATORIOS):
        return False, None
    if re.search(r"autoriza", t):
        return True, "autorizado"
    if re.search(r"previsto|previsao de|estuda|planeja realizar|intencao de realizar|anuncia", t):
        return True, "previsto"
    if any(re.search(p, t) for p in PADRAO_ABERTAS):
        return True, "inscricoes_abertas"
    if re.search(r"edital (de abertura|de concurso|n[ºo°]|publicado)|divulgacao do edital|publica edital|editais", t):
        return True, "edital_publicado"
    return True, padrao


def _marcar(texto: str, dicionario: dict) -> list:
    t = normalizar(texto)
    marcas = []
    for nome, padroes in dicionario.items():
        if any(re.search(p, t) for p in padroes):
            marcas.append(nome)
    return marcas


def tag_areas(texto: str) -> list:
    areas = _marcar(texto, AREAS)
    return areas or ["Administrativa"]


def tag_cursos(texto: str) -> list:
    return _marcar(texto, CURSOS)
