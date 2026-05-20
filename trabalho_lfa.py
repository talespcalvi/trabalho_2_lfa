import itertools
import sys
from collections import defaultdict

class Gramatica:
    def __init__(self):
        self.variaveis = set()
        self.terminais = set()
        self.inicial = ""
        self.transicoes = defaultdict(list)
    
    def carregar_arquivo(self, caminho_arquivo):
        with open(caminho_arquivo, 'r', encoding='utf-8') as f:
            linhas = [l.strip() for l in f if l.strip()]
            
        modo = ""
        for linha in linhas:
            if linha.startswith("Variáveis:"):
                self.variaveis = set(linha.split(":")[1].replace(" ", ""))
            elif linha.startswith("Terminais:"):
                term_str = linha.split(":")[1].strip()
                # Separar os terminais (considerando 'eps' como um token especial)
                self.terminais = set([t for t in term_str.split(" ") if t])
            elif linha.startswith("Simbolo inicial:"):
                self.inicial = linha.split(":")[1].strip()
            elif linha.startswith("Transições:"):
                modo = "transicoes"
            elif modo == "transicoes":
                # O espaço separa o lado esquerdo (LHS) do lado direito (RHS)
                partes = linha.split(" ", 1)
                if len(partes) == 2:
                    lhs = partes[0].strip()
                    rhs = partes[1].strip()
                    self.transicoes[lhs].append(self._tokenizar_rhs(rhs))
                    
    def _tokenizar_rhs(self, rhs_str):
        if rhs_str == "eps":
            return ["eps"]
        tokens = []
        for char in rhs_str:
            tokens.append(char)
        return tokens

    def salvar_arquivo(self, caminho_arquivo, titulo="Gramática"):
        with open(caminho_arquivo, 'w', encoding='utf-8') as f:
            f.write(f"--- {titulo} ---\n")
            f.write(f"Variáveis: {' '.join(self.variaveis)}\n")
            f.write(f"Terminais: {' '.join(self.terminais)}\n")
            f.write(f"Simbolo inicial: {self.inicial}\n")
            f.write("Transições:\n")
            for lhs, rhss in self.transicoes.items():
                for rhs in rhss:
                    rhs_str = "".join(rhs)
                    f.write(f"{lhs} {rhs_str}\n")

    # ==========================================
    # PARTE 1: LIMPEZA DA GRAMÁTICA
    # ==========================================
    def limpar_gramatica(self):
        self._remover_producoes_vazias()
        self._remover_producoes_unidade()
        self._remover_producoes_inuteis()

    def _remover_producoes_vazias(self):
        # 1. Encontrar variáveis anuláveis (que geram 'eps')
        anulaveis = set()
        mudou = True
        while mudou:
            mudou = False
            for lhs, rhss in self.transicoes.items():
                if lhs in anulaveis: continue
                for rhs in rhss:
                    if rhs == ["eps"] or all(sym in anulaveis for sym in rhs):
                        anulaveis.add(lhs)
                        mudou = True
                        break

        # 2. Gerar combinações sem as variáveis anuláveis
        novas_transicoes = defaultdict(list)
        for lhs, rhss in self.transicoes.items():
            for rhs in rhss:
                if rhs == ["eps"]: continue
                
                indices_anulaveis = [i for i, sym in enumerate(rhs) if sym in anulaveis]
                num_anulaveis = len(indices_anulaveis)
                
                # Gerar todas as sub-combinações (potência)
                for r in range(num_anulaveis + 1):
                    para_remover = list(itertools.combinations(indices_anulaveis, r))
                    for remocao in para_remover:
                        novo_rhs = [sym for i, sym in enumerate(rhs) if i not in remocao]
                        if novo_rhs and novo_rhs not in novas_transicoes[lhs]:
                            novas_transicoes[lhs].append(novo_rhs)
                            
        self.transicoes = novas_transicoes

    def _remover_producoes_unidade(self):
        pares_unidade = set((v, v) for v in self.variaveis)
        mudou = True
        while mudou:
            mudou = False
            novos_pares = set()
            for A, B in pares_unidade:
                for rhs in self.transicoes.get(B, []):
                    if len(rhs) == 1 and rhs[0] in self.variaveis:
                        C = rhs[0]
                        if (A, C) not in pares_unidade:
                            novos_pares.add((A, C))
                            mudou = True
            pares_unidade.update(novos_pares)

        novas_transicoes = defaultdict(list)
        for A, B in pares_unidade:
            for rhs in self.transicoes.get(B, []):
                if not (len(rhs) == 1 and rhs[0] in self.variaveis): # Não é unidade
                    if rhs not in novas_transicoes[A]:
                        novas_transicoes[A].append(rhs)
                        
        self.transicoes = novas_transicoes

    def _remover_producoes_inuteis(self):
        # 1. Variáveis Geradoras
        geradoras = set()
        mudou = True
        while mudou:
            mudou = False
            for lhs, rhss in self.transicoes.items():
                if lhs in geradoras: continue
                for rhs in rhss:
                    if all(sym in self.terminais or sym in geradoras for sym in rhs):
                        geradoras.add(lhs)
                        mudou = True
                        break

        # Filtrar produções não geradoras
        trans_geradoras = defaultdict(list)
        for lhs, rhss in self.transicoes.items():
            if lhs in geradoras:
                for rhs in rhss:
                    if all(sym in self.terminais or sym in geradoras for sym in rhs):
                        trans_geradoras[lhs].append(rhs)
        self.transicoes = trans_geradoras

        # 2. Variáveis Alcançáveis
        alcancaveis = set([self.inicial])
        fila = [self.inicial]
        while fila:
            atual = fila.pop(0)
            for rhs in self.transicoes.get(atual, []):
                for sym in rhs:
                    if sym in self.variaveis and sym not in alcancaveis:
                        alcancaveis.add(sym)
                        fila.append(sym)

        # Filtrar não alcançáveis
        trans_finais = defaultdict(list)
        for lhs, rhss in self.transicoes.items():
            if lhs in alcancaveis:
                trans_finais[lhs] = rhss
        
        self.transicoes = trans_finais
        self.variaveis = geradoras.intersection(alcancaveis)

    # ==========================================
    # PARTE 2: FORMA NORMAL DE CHOMSKY (CNF)
    # ==========================================
    def converter_para_cnf(self):
        novas_transicoes = defaultdict(list)
        contador_var = 1
        mapa_terminais = {}

        # Passo 1: Separar terminais de variáveis em produções de tamanho >= 2
        for lhs, rhss in self.transicoes.items():
            for rhs in rhss:
                if len(rhs) >= 2:
                    novo_rhs = []
                    for sym in rhs:
                        if sym in self.terminais:
                            if sym not in mapa_terminais:
                                nova_var = f"X_{sym}"
                                mapa_terminais[sym] = nova_var
                                self.variaveis.add(nova_var)
                                novas_transicoes[nova_var].append([sym])
                            novo_rhs.append(mapa_terminais[sym])
                        else:
                            novo_rhs.append(sym)
                    novas_transicoes[lhs].append(novo_rhs)
                else:
                    novas_transicoes[lhs].append(rhs)

        # Passo 2: Reduzir produções longas (tamanho >= 3)
        transicoes_cnf = defaultdict(list)
        for lhs, rhss in novas_transicoes.items():
            for rhs in rhss:
                atual_lhs = lhs
                atual_rhs = rhs
                while len(atual_rhs) > 2:
                    nova_var = f"Z{contador_var}"
                    contador_var += 1
                    self.variaveis.add(nova_var)
                    
                    transicoes_cnf[atual_lhs].append([atual_rhs[0], nova_var])
                    atual_lhs = nova_var
                    atual_rhs = atual_rhs[1:]
                transicoes_cnf[atual_lhs].append(atual_rhs)
                
        self.transicoes = transicoes_cnf

    # ==========================================
    # PARTE 3: TESTE DA GRAMÁTICA (Derivação)
    # ==========================================
    def testar_palavra(self, palavra_str):
        palavra = list(palavra_str) # Assume que terminais são de 1 caractere na palavra de teste
        n = len(palavra)
        if n == 0:
            print("Palavra vazia não suportada no teste CNF padrão sem epsilon.")
            return

        # Inicializa tabela CYK
        # Tabela armazenará tuplas: (Variável_Geradora, Regra_Usada_Str, Posição_Corte, Filho_Esq, Filho_Dir)
        tabela = [[[] for _ in range(n)] for _ in range(n)]

        # Base do CYK (tamanho 1)
        for i in range(n):
            terminal = palavra[i]
            for lhs, rhss in self.transicoes.items():
                for rhs in rhss:
                    if len(rhs) == 1 and rhs[0] == terminal:
                        tabela[i][i].append((lhs, f"{lhs} -> {terminal}", None, None, None))

        # Passo Indutivo CYK (tamanho >= 2)
        for l in range(2, n + 1):
            for i in range(n - l + 1):
                j = i + l - 1
                for k in range(i, j):
                    esquerdos = tabela[i][k]
                    direitos = tabela[k+1][j]
                    for (var_esq, _, _, _, _) in esquerdos:
                        for (var_dir, _, _, _, _) in direitos:
                            for lhs, rhss in self.transicoes.items():
                                for rhs in rhss:
                                    if len(rhs) == 2 and rhs[0] == var_esq and rhs[1] == var_dir:
                                        tabela[i][j].append((
                                            lhs, 
                                            f"{lhs} -> {var_esq}{var_dir}",
                                            k,
                                            (var_esq, i, k),
                                            (var_dir, k+1, j)
                                        ))

        # Verificar se aceita
        aceito = False
        raiz_derivação = None
        for item in tabela[0][n-1]:
            if item[0] == self.inicial:
                aceito = True
                raiz_derivação = item
                break

        print(f"\n--- Teste da Palavra: '{palavra_str}' ---")
        if not aceito:
            print("A palavra NÃO é reconhecida pela gramática.")
        else:
            print("Palavra reconhecida! Gerando passo a passo:")
            self._imprimir_derivacao(tabela, 0, n-1, self.inicial, palavra_str)

    def _imprimir_derivacao(self, tabela, i, j, variavel_alvo, palavra_original):
        # Constrói a árvore a partir dos backpointers do CYK
        def extrair_arvore(r_i, r_j, var):
            for item in tabela[r_i][r_j]:
                if item[0] == var:
                    return item # Retorna a tupla do nó
            return None

        raiz = extrair_arvore(i, j, variavel_alvo)
        
        # Algoritmo simples de derivação mais à esquerda (Leftmost Derivation)
        forma_sentencial = [variavel_alvo]
        
        # Para simular a derivação, usaremos uma pilha de substituições rastreando a árvore
        # Como o CYK nos dá uma árvore completa, vamos percorrê-la e aplicar as regras no nosso array
        
        def obter_folhas_arvore(no_info, b_i, b_j):
            _, regra, k, f_esq, f_dir = no_info
            if f_esq is None and f_dir is None:
                # É uma regra para terminal A -> a
                return regra
            
            # Precisamos substituir a primeira variável que encontrar
            # Para impressão iterativa:
            pass
            
        # Como a exigência é mostrar a aplicação sequencial[cite: 31, 32]:
        nos_pendentes = [(raiz, i, j)]
        forma_atual = [variavel_alvo]
        
        print(f"{''.join(forma_atual)}")
        
        # Fazendo uma travessia DFS (Derivação mais à esquerda)
        # Vamos reconstruir a árvore completa em memória primeiro para facilitar
        class No:
            def __init__(self, var, regra, f_esq=None, f_dir=None):
                self.var = var
                self.regra = regra
                self.f_esq = f_esq
                self.f_dir = f_dir

        def construir_arvore(r_i, r_j, var):
            info = extrair_arvore(r_i, r_j, var)
            _, regra, k, f_esq, f_dir = info
            if f_esq is None:
                return No(var, regra)
            return No(var, regra, construir_arvore(f_esq[1], f_esq[2], f_esq[0]), construir_arvore(f_dir[1], f_dir[2], f_dir[0]))

        arvore_raiz = construir_arvore(i, j, variavel_alvo)
        
        # Simula a derivação
        cadeia = [arvore_raiz]
        while any(isinstance(x, No) for x in cadeia):
            for idx, elemento in enumerate(cadeia):
                if isinstance(elemento, No):
                    regra_aplicada = elemento.regra
                    print(f"  (Aplica regra: {regra_aplicada})")
                    
                    if elemento.f_esq is None: # Vai para terminal
                        cadeia[idx] = regra_aplicada.split("->")[1].strip()
                    else:
                        cadeia = cadeia[:idx] + [elemento.f_esq, elemento.f_dir] + cadeia[idx+1:]
                    
                    # Imprime estado atual
                    estado_str = ""
                    for x in cadeia:
                        if isinstance(x, No): estado_str += x.var
                        else: estado_str += x
                    print(f"{estado_str}")
                    break


# ==========================================
# EXECUÇÃO PRINCIPAL
# ==========================================
if __name__ == "__main__":
    g = Gramatica()
    print("1. Carregando Gramática do arquivo 'entrada.txt'...")
    try:
        g.carregar_arquivo("entrada.txt")
    except FileNotFoundError:
        print("Erro: Crie um arquivo 'entrada.txt' no mesmo diretório seguindo o formato do trabalho.")
        sys.exit(1)

    print("\n--- Parte 1: Limpeza da Gramática ---")
    g.limpar_gramatica()
    g.salvar_arquivo("saida_limpa.txt", "Gramática Limpa")
    print("Gramática limpa salva em 'saida_limpa.txt'.")

    print("\n--- Parte 2: Conversão para Forma Normal de Chomsky ---")
    g.converter_para_cnf()
    g.salvar_arquivo("saida_cnf.txt", "Gramática na Forma Normal de Chomsky")
    print("Gramática CNF salva em 'saida_cnf.txt'.")

    print("\n--- Parte 3: Teste de Palavras ---")
    # Altere as palavras abaixo conforme as palavras suportadas pela sua gramática original
    palavras_teste = ["aba", "ab"] 
    for p in palavras_teste:
        g.testar_palavra(p)