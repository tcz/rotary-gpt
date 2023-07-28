import math

class PCMUSilenceDetector:
    def __init__(self):
        self.sample_counter = 0
        self.current_samples = b""
        self.skip_before_silence_sample_count = 0.5 / 0.02 # 0.5 seconds
        self.silence_sample_count = 0.5 / 0.02 # 0.5 seconds
        self.sample_count = 0.5 / 0.02  # 0.5 seconds
        self.silence_upper_threshold = None
        self.signal_lower_threshold = None
        self.had_signal = False

    def add_sample_and_detect_silence(self, chunk):
        if self.sample_counter < self.skip_before_silence_sample_count:
            self.sample_counter += 1
            return

        if self.sample_counter < self.silence_sample_count + self.skip_before_silence_sample_count:
            self.current_samples = self.current_samples + chunk
            self.sample_counter += 1
            return

        if self.silence_upper_threshold is None:
            self.silence_upper_threshold = self._calculate_level(self.current_samples) * 2
            self.signal_lower_threshold = self.silence_upper_threshold * 5
            self.current_samples = b""

        self.current_samples = self.current_samples + chunk

        if self.sample_counter < self.silence_sample_count + self.skip_before_silence_sample_count + self.sample_count:
            self.sample_counter += 1
            return

        level = self._calculate_level(self.current_samples)
        silence_detected = False

        if level > self.signal_lower_threshold:
            self.had_signal = True
        elif self.had_signal and level < self.silence_upper_threshold:
            self.had_signal = False
            silence_detected = True


        self.current_samples = self.current_samples[len(chunk):]
        return silence_detected

    def reset_had_signal(self):
        self.had_signal = False

    def _calculate_level(self, samples):
        total = 0

        for i in range(len(samples)):
            linear = mu_law_linear_to_sample(samples[i])
            total = total + linear * linear

        return math.sqrt(total / len(samples))

# https://docs.fileformat.com/audio/wav/
def wave_header():
    sample_rate = 8000
    bits_per_sample = 8
    channels = 1

    header = b""
    header = header + b"RIFF"
    # We don't know the file size yet, opting for maximum
    header = header + 0xffffffff.to_bytes(4, 'little')
    header = header + b"WAVEfmt "
    header = header + len(header).to_bytes(4, 'little')
    # ITU G.711 u-law (PCMU) = 0x0007
    header = header + 0x0007.to_bytes(2, 'little')

    header = header + channels.to_bytes(2, 'little')
    header = header + sample_rate.to_bytes(4, 'little')
    header = header + int(sample_rate * bits_per_sample * channels / 8).to_bytes(4, 'little')
    header = header + int(bits_per_sample * channels / 8).to_bytes(2, 'little')
    header = header + bits_per_sample.to_bytes(2, 'little')
    header = header + b"data"
    # We don't know the data size yet, opting for maximum
    header = header + 0xffffffff.to_bytes(4, 'little')

    return header


bias = 0x84
clip = 32635

# http://web.archive.org/web/20110719132013/http://hazelware.luggle.com/tutorials/mulawcompression.html
# http://what-when-how.com/voip/g-711-compression-voip/
mu_law_compress_table = [
    0,0,1,1,2,2,2,2,3,3,3,3,3,3,3,3,
    4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,
    5,5,5,5,5,5,5,5,5,5,5,5,5,5,5,5,
    5,5,5,5,5,5,5,5,5,5,5,5,5,5,5,5,
    6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,
    6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,
    6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,
    6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,
    7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,
    7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,
    7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,
    7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,
    7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,
    7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,
    7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,
    7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7
]

def linear_to_mu_law_sample(sample):
    sign = (sample >> 8) & 0x80
    if sign:
        sample = -sample
    if sample > clip:
        sample = clip
    sample = sample + bias
    exponent = mu_law_compress_table[(sample >> 7) & 0xFF]
    mantissa = (sample >> (exponent+3)) & 0x0F
    compressedByte = ~(sign | (exponent << 4) | mantissa)
    return compressedByte & 0xFF

mu_decompress_table = [
    -32124,-31100,-30076,-29052,-28028,-27004,-25980,-24956,
    -23932,-22908,-21884,-20860,-19836,-18812,-17788,-16764,
    -15996,-15484,-14972,-14460,-13948,-13436,-12924,-12412,
    -11900,-11388,-10876,-10364, -9852, -9340, -8828, -8316,
    -7932, -7676, -7420, -7164, -6908, -6652, -6396, -6140,
    -5884, -5628, -5372, -5116, -4860, -4604, -4348, -4092,
    -3900, -3772, -3644, -3516, -3388, -3260, -3132, -3004,
    -2876, -2748, -2620, -2492, -2364, -2236, -2108, -1980,
    -1884, -1820, -1756, -1692, -1628, -1564, -1500, -1436,
    -1372, -1308, -1244, -1180, -1116, -1052,  -988,  -924,
    -876,  -844,  -812,  -780,  -748,  -716,  -684,  -652,
    -620,  -588,  -556,  -524,  -492,  -460,  -428,  -396,
    -372,  -356,  -340,  -324,  -308,  -292,  -276,  -260,
    -244,  -228,  -212,  -196,  -180,  -164,  -148,  -132,
    -120,  -112,  -104,   -96,   -88,   -80,   -72,   -64,
    -56,   -48,   -40,   -32,   -24,   -16,    -8,     0,
    32124, 31100, 30076, 29052, 28028, 27004, 25980, 24956,
    23932, 22908, 21884, 20860, 19836, 18812, 17788, 16764,
    15996, 15484, 14972, 14460, 13948, 13436, 12924, 12412,
    11900, 11388, 10876, 10364,  9852,  9340,  8828,  8316,
    7932,  7676,  7420,  7164,  6908,  6652,  6396,  6140,
    5884,  5628,  5372,  5116,  4860,  4604,  4348,  4092,
    3900,  3772,  3644,  3516,  3388,  3260,  3132,  3004,
    2876,  2748,  2620,  2492,  2364,  2236,  2108,  1980,
    1884,  1820,  1756,  1692,  1628,  1564,  1500,  1436,
    1372,  1308,  1244,  1180,  1116,  1052,   988,   924,
    876,   844,   812,   780,   748,   716,   684,   652,
    620,   588,   556,   524,   492,   460,   428,   396,
    372,   356,   340,   324,   308,   292,   276,   260,
    244,   228,   212,   196,   180,   164,   148,   132,
    120,   112,   104,    96,    88,    80,    72,    64,
    56,    48,    40,    32,    24,    16,     8,     0
]

def mu_law_linear_to_sample(byte):
    return mu_decompress_table[byte]

