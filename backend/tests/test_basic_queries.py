#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Suite de testes básicos para validar integridade dos dados
Testa: Conexão, existência de tabelas, contagem, queries básicas
"""

import sys
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

try:
    from clickhouse_driver import Client
except ImportError:
    logger.error("❌ clickhouse-driver não instalado. Execute: pip install clickhouse-driver")
    sys.exit(1)


class TestClickHouseData:
    """Testes de integridade de dados"""
    
    def __init__(self, host='localhost', port=9000, user='admin', password='admin'):
        """Inicializa conexão"""
        try:
            self.client = Client(host, port=port, user=user, password=password)
            self.client.execute("SELECT 1")
            logger.info(f"✅ Conectado ao ClickHouse em {host}:{port}")
            self.passed = 0
            self.failed = 0
        except Exception as e:
            logger.error(f"❌ Erro ao conectar: {e}")
            raise
    
    def test(self, name, query, validate_fn=None):
        """
        Executa um teste
        
        Args:
            name: Nome do teste
            query: Query SQL
            validate_fn: Função para validar resultado (opcional)
        """
        try:
            result = self.client.execute(query)
            if validate_fn and not validate_fn(result):
                logger.error(f"❌ {name}")
                self.failed += 1
                return False
            logger.info(f"✅ {name}")
            self.passed += 1
            return True
        except Exception as e:
            logger.error(f"❌ {name}: {e}")
            self.failed += 1
            return False
    
    def run_all_tests(self):
        """Executa suite completa de testes"""
        
        logger.info("\n" + "="*80)
        logger.info("🧪 TESTES BÁSICOS - EASYDATASUS")
        logger.info("="*80 + "\n")
        
        # ========== TESTES SRAG ==========
        logger.info("📊 SRAG - Síndrome Respiratória Aguda Grave")
        logger.info("-"*80)
        
        self.test(
            "Tabela SRAG existe",
            "SELECT 1 FROM srag LIMIT 1",
            lambda r: len(r) >= 0
        )
        
        self.test(
            "SRAG tem dados",
            "SELECT COUNT(*) FROM srag",
            lambda r: r[0][0] > 0
        )
        
        result = self.client.execute("SELECT COUNT(*) FROM srag")[0][0]
        logger.info(f"   └─ {result:,} registros\n")
        
        self.test(
            "SRAG: Datas válidas",
            "SELECT MIN(dt_notific), MAX(dt_notific) FROM srag",
            lambda r: r[0][0] is not None and r[0][1] is not None
        )
        
        result = self.client.execute(
            "SELECT MIN(dt_notific), MAX(dt_notific) FROM srag"
        )[0]
        logger.info(f"   └─ Período: {result[0]} a {result[1]}\n")
        
        self.test(
            "SRAG: Estados variados",
            "SELECT COUNT(DISTINCT sg_uf_not) FROM srag",
            lambda r: r[0][0] >= 5
        )
        
        result = self.client.execute(
            "SELECT COUNT(DISTINCT sg_uf_not) FROM srag"
        )[0][0]
        logger.info(f"   └─ {result} estados diferentes\n")
        
        self.test(
            "SRAG: Hospitalizações registradas",
            "SELECT COUNT(*) FROM srag WHERE hospital = 1",
            lambda r: r[0][0] > 0
        )
        
        result = self.client.execute(
            "SELECT COUNT(*) FROM srag WHERE hospital = 1"
        )[0][0]
        logger.info(f"   └─ {result:,} casos hospitalizados\n")
        
        self.test(
            "SRAG: Óbitos registrados",
            "SELECT COUNT(*) FROM srag WHERE evolucao = 2",
            lambda r: r[0][0] >= 0  # Pode ter 0
        )
        
        result = self.client.execute(
            "SELECT COUNT(*) FROM srag WHERE evolucao = 2"
        )[0][0]
        logger.info(f"   └─ {result:,} óbitos\n")
        
        self.test(
            "SRAG: Taxa de hospitalizaçãoCalculável",
            """
            SELECT 
                ROUND(SUM(IF(hospital=1, 1, 0)) / COUNT(*) * 100, 2) as taxa
            FROM srag
            """,
            lambda r: isinstance(r[0][0], (int, float))
        )
        
        # ========== TESTES ATENÇÃO BÁSICA ==========
        logger.info("🏥 ATENÇÃO BÁSICA - Unidades Básicas de Saúde")
        logger.info("-"*80)
        
        self.test(
            "Tabela Atenção Básica existe",
            "SELECT 1 FROM atencao_basica LIMIT 1",
            lambda r: len(r) >= 0
        )
        
        self.test(
            "Atenção Básica tem dados",
            "SELECT COUNT(*) FROM atencao_basica",
            lambda r: r[0][0] > 0
        )
        
        result = self.client.execute("SELECT COUNT(*) FROM atencao_basica")[0][0]
        logger.info(f"   └─ {result:,} UBS cadastradas\n")
        
        self.test(
            "Atenção Básica: Estados cobertos",
            "SELECT COUNT(DISTINCT uf) FROM atencao_basica",
            lambda r: r[0][0] >= 20  # Deve ter maioria dos estados
        )
        
        result = self.client.execute(
            "SELECT COUNT(DISTINCT uf) FROM atencao_basica"
        )[0][0]
        logger.info(f"   └─ {result} estados com UBS\n")
        
        self.test(
            "Atenção Básica: Municípios cobertos",
            "SELECT COUNT(DISTINCT ibge) FROM atencao_basica",
            lambda r: r[0][0] > 1000
        )
        
        result = self.client.execute(
            "SELECT COUNT(DISTINCT ibge) FROM atencao_basica"
        )[0][0]
        logger.info(f"   └─ {result:,} municípios\n")
        
        self.test(
            "Atenção Básica: Coordenadas geográficas válidas",
            """
            SELECT COUNT(*) FROM atencao_basica 
            WHERE latitude != 0 AND longitude != 0
            """,
            lambda r: r[0][0] > 0
        )
        
        result = self.client.execute(
            "SELECT COUNT(*) FROM atencao_basica WHERE latitude != 0"
        )[0][0]
        logger.info(f"   └─ {result:,} UBS com coordenadas\n")
        
        # ========== TESTES INTEROPERABILIDADE ==========
        logger.info("🔗 INTEROPERABILIDADE - Queries entre bases")
        logger.info("-"*80)
        
        self.test(
            "JOIN: SRAG x Atenção Básica por município",
            """
            SELECT COUNT(*) FROM srag s
            INNER JOIN atencao_basica a ON s.co_mun_not = a.ibge
            LIMIT 10
            """,
            lambda r: len(r) > 0
        )
        
        result = self.client.execute(
            """
            SELECT COUNT(DISTINCT s.co_mun_not) as municipios_com_ambos
            FROM srag s
            INNER JOIN atencao_basica a ON s.co_mun_not = a.ibge
            """
        )[0][0]
        logger.info(f"   └─ {result:,} municípios com dados em ambas as bases\n")
        
        self.test(
            "Casos SRAG por UF (agregação)",
            """
            SELECT 
                sg_uf_not,
                COUNT(*) as total
            FROM srag
            GROUP BY sg_uf_not
            ORDER BY total DESC
            LIMIT 5
            """,
            lambda r: len(r) >= 5
        )
        
        # ========== RESUMO ==========
        logger.info("\n" + "="*80)
        logger.info("📋 RESUMO DOS TESTES")
        logger.info("="*80)
        logger.info(f"✅ Passou: {self.passed}")
        logger.info(f"❌ Falhou: {self.failed}")
        logger.info(f"Total: {self.passed + self.failed}")
        
        if self.failed == 0:
            logger.info("\n✅ TODOS OS TESTES PASSARAM!")
            return True
        else:
            logger.warning(f"\n⚠️  {self.failed} teste(s) falharam")
            return False


def main():
    """Executa todos os testes"""
    try:
        tester = TestClickHouseData()
        success = tester.run_all_tests()
        return 0 if success else 1
    except Exception as e:
        logger.error(f"❌ Erro fatal: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
