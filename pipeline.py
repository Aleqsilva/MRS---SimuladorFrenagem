# pipeline.py
import grade, corrida


def _run_from_grades(*, grades, progressiva, crescente, velocidade_inicial_kmh,
                     passo_de_tempo_s, tempo_freio_minimo_s, tempo_equalizacao_freio_s,
                     taxa_frenagem, tamanho_trem, step, inserir_primeiro_valor,
                     regras_operacionais=None):
    if inserir_primeiro_valor:
        grades = grade.insere_primeiro_valor(grades, tamanho_trem)

    linhas, fieldnames = grade.geraTabelaIteracoesGradePorArea(
        grades, tamanho_trem, step, progressiva_inicial=progressiva, crescente=crescente
    )
    serie = grade.extraiSerieGradeTotal(linhas, crescente)

    serie_progressiva = [row["progressiva"] for row in serie]
    serie_grade_total = [row["grade_total"] for row in serie]
    
    corrida_linhas = corrida.simulaAbaCorrida(
        serie_progressiva, serie_grade_total,
        progressiva_inicial=progressiva,
        velocidade_inicial_kmh=velocidade_inicial_kmh,
        crescente=crescente,
        passo_de_tempo_s=passo_de_tempo_s,
        tempo_freio_minimo_s=tempo_freio_minimo_s,
        tempo_equalizacao_freio_s=tempo_equalizacao_freio_s,
        taxa_frenagem=taxa_frenagem,
        regras_operacionais=regras_operacionais,
    )

    return {
        "linhas": linhas,
        "fieldnames": fieldnames,
        "serie": serie,
        "corrida": corrida_linhas,
    }


def run_pipeline(*, csv_path, progressiva, ponto_a_proteger, crescente, velocidade_inicial_kmh,
                 passo_de_tempo_s, tempo_freio_minimo_s, tempo_equalizacao_freio_s,
                 taxa_frenagem, tamanho_trem, step, regras_operacionais=None):
    grades = grade.leGradeCsv(csv_path, crescente)
    return _run_from_grades(
        grades=grades,
        progressiva=progressiva,
        crescente=crescente,
        velocidade_inicial_kmh=velocidade_inicial_kmh,
        passo_de_tempo_s=passo_de_tempo_s,
        tempo_freio_minimo_s=tempo_freio_minimo_s,
        tempo_equalizacao_freio_s=tempo_equalizacao_freio_s,
        taxa_frenagem=taxa_frenagem,
        tamanho_trem=tamanho_trem,
        step=step,
        inserir_primeiro_valor=True,
        regras_operacionais=regras_operacionais,
    )


def run_pipeline_livre(*, csv_path, progressiva, crescente, velocidade_inicial_kmh,
                       passo_de_tempo_s, tempo_freio_minimo_s, tempo_equalizacao_freio_s,
                       taxa_frenagem, tamanho_trem, step, regras_operacionais=None):
    grades = grade.leGradeCsvLivre(csv_path, crescente)
    return _run_from_grades(
        grades=grades,
        progressiva=progressiva,
        crescente=crescente,
        velocidade_inicial_kmh=velocidade_inicial_kmh,
        passo_de_tempo_s=passo_de_tempo_s,
        tempo_freio_minimo_s=tempo_freio_minimo_s,
        tempo_equalizacao_freio_s=tempo_equalizacao_freio_s,
        taxa_frenagem=taxa_frenagem,
        tamanho_trem=tamanho_trem,
        step=step,
        inserir_primeiro_valor=False,
        regras_operacionais=regras_operacionais,
    )