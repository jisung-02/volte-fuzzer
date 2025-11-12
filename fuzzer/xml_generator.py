import xml.etree.ElementTree as ET
from xml.dom import minidom
from typing import List
import random
import string

class SIPpXMLGenerator:
    """SIPp XML 시나리오 동적 생성 및 변조"""
    
    def __init__(self, template_path: str):
        self.tree = ET.parse(template_path)
        self.root = self.tree.getroot()
        
    def mutate_header(self, header_name: str, mutation_type: str) -> None:
        """SIP 헤더 변조
        
        Args:
            header_name: Via, From, To, Contact, etc.
            mutation_type: overflow, format_string, special_chars, null_byte
        """
        mutations = {
            'overflow': lambda: 'A' * random.randint(1000, 10000),
            'format_string': lambda: '%s%s%s%n%n%n' * random.randint(10, 100),
            'special_chars': lambda: ''.join(random.choices('\\x00\\r\\n<>\"\'', k=100)),
            'null_byte': lambda: 'test\\x00' + 'A' * 100,
            'unicode': lambda: ''.join(chr(random.randint(0x4e00, 0x9fff)) for _ in range(50)),
            'long_param': lambda: f'param={("A" * 5000)}',
        }
        
        mutation_value = mutations.get(mutation_type, lambda: 'FUZZ')()
        
        # XML에서 해당 헤더 찾아 변조
        for send_elem in self.root.findall('.//send'):
            cdata = send_elem.text
            if header_name in cdata:
                # 헤더 값 변조
                mutated = self._replace_header_value(cdata, header_name, mutation_value)
                send_elem.text = mutated
                
    def _replace_header_value(self, sip_message: str, header: str, value: str) -> str:
        """SIP 메시지에서 특정 헤더 값 교체"""
        lines = sip_message.split('\\n')
        for i, line in enumerate(lines):
            if line.startswith(header + ':'):
                lines[i] = f'{header}: {value}'
                break
        return '\\n'.join(lines)
    
    def add_malformed_header(self, header_name: str, value: str) -> None:
        """악의적인 헤더 추가"""
        for send_elem in self.root.findall('.//send'):
            cdata = send_elem.text
            # SIP 메시지 끝에 헤더 추가
            lines = cdata.split('\\n')
            insert_pos = -2  # Content-Length 앞에 삽입
            lines.insert(insert_pos, f'{header_name}: {value}')
            send_elem.text = '\\n'.join(lines)
    
    def mutate_sdp_body(self, mutation_type: str) -> None:
        """SDP body 변조 (INVITE 메시지)"""
        sdp_mutations = {
            'invalid_ip': '999.999.999.999',
            'overflow_session': 's=' + 'A' * 10000,
            'negative_port': 'm=audio -1 RTP/AVP 0',
            'huge_bandwidth': 'b=AS:999999999',
            'malformed_rtpmap': 'a=rtpmap:AAAA PCMU/8000',
        }
        
        mutation = sdp_mutations.get(mutation_type, 'v=FUZZ')
        
        # SDP 부분 찾아 변조
        for send_elem in self.root.findall('.//send'):
            cdata = send_elem.text
            if 'v=0' in cdata:  # SDP 포함 여부 확인
                cdata = cdata.replace('v=0', mutation)
                send_elem.text = cdata
    
    def set_authentication(self, username: str, aka_k: str, aka_op: str, aka_amf: str) -> None:
        """인증 정보 설정"""
        # [authentication] 키워드 파라미터 변조
        for send_elem in self.root.findall('.//send'):
            cdata = send_elem.text
            if '[authentication]' in cdata:
                # 인증 파라미터 변조
                auth_line = f'[authentication username={username} aka_K={aka_k} aka_OP={aka_op} aka_AMF={aka_amf}]'
                cdata = cdata.replace('[authentication]', auth_line)
                send_elem.text = cdata
    
    def save(self, output_path: str) -> None:
        """변조된 XML 저장"""
        xml_str = ET.tostring(self.root, encoding='unicode')
        
        # Pretty print
        dom = minidom.parseString(xml_str)
        pretty_xml = dom.toprettyxml(indent='  ')
        
        with open(output_path, 'w') as f:
            f.write(pretty_xml)
    
    def generate_fuzz_variations(self, base_name: str, output_dir: str, count: int) -> List[str]:
        """여러 퍼징 변형 생성"""
        variations = []
        
        mutation_strategies = [
            ('Via', 'overflow'),
            ('From', 'format_string'),
            ('To', 'special_chars'),
            ('Call-ID', 'null_byte'),
            ('Contact', 'unicode'),
            ('User-Agent', 'long_param'),
        ]
        
        for i in range(count):
            # 무작위 변조 선택
            header, mutation = random.choice(mutation_strategies)
            
            # 새 인스턴스 생성 (원본 보존)
            gen = SIPpXMLGenerator(self.tree)
            gen.mutate_header(header, mutation)
            
            # 악의적 헤더 추가 (확률적)
            if random.random() > 0.7:
                gen.add_malformed_header(
                    f'X-Fuzz-{i}',
                    ''.join(random.choices(string.printable, k=500))
                )
            
            output_path = f'{output_dir}/{base_name}_fuzz_{i:04d}.xml'
            gen.save(output_path)
            variations.append(output_path)
        
        return variations