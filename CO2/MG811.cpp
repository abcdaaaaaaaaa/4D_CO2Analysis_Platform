#include "MG811.h"
#include <math.h>

MG811::MG811(int bitadc, byte pin)
{
    _bitadc = pow(2, bitadc) - 1;
    _pin = pin;
}

struct GasData { float minppm, maxppm, emf_min, emf_max; };

GasData gases[] = {
    {100, 600, 323.217, 324.2145}, // CH4
    {100, 1000, 320.6234, 323.616}, // C2H5OH
    {100, 10000, 264.1646, 323.616}, // CO
    {400, 1000, 303.6658, 324.2145}  // CO2
};

void MG811::begin() {
    pinMode(_pin, INPUT);
}

float MG811::read() {
    int adc = analogRead(_pin);
    return 1.0 - ((float)adc / (float)_bitadc); // Because the MG811 sensor operates based on voltage rather than direct proportional signal, unlike other analog sensors, the value must be inverted.
}

float MG811::fmap(float x, float in_min, float in_max, float out_min, float out_max) {
    return (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min;
}

float MG811::inverseYaxb(float a, float y, float b) {
    return pow(y / a, 1.0 / b);
}

float MG811::correction_time(float t) {
    return (t < 20) ? t : fmod(t, 20.0);
}

float MG811::time_curve(float x) {
    if (x <= 1) return 325.79;
    else if (x <= 2) return fmap(x, 1, 2, 325.79, 326.15);
    else if (x <= 3) return fmap(x, 2, 3, 326.15, 325.05);
    else if (x <= 5) return fmap(x, 3, 5, 325.05, 288.06);
    else if (x <= 7) return 285.86 + (3.2 * pow(x - 4, -1.0587) - 1);
    else if (x <= 11) return 285.86;
    else if (x <= 13) return 285.86 + (3.2 * pow(14 - x, -1.0587) - 1);
    else if (x <= 15) return fmap(x, 13, 15, 288.06, 319.93);
    else if (x <= 17) return 324.87 - (5.94 * pow(x - 14, -1.6218) - 1);
    else if (x <= 19) return 324.87;
    else if (x <= 20) return fmap(x, 19, 20, 324.87, 325.79);
    else return NAN;
}

float MG811::calculateCorrection(float x) {
    float temp_corr_a = fmap(28, 20, 30, 523.094, 527.0596);
    float temp_corr_b = fmap(28, 20, 30, -0.0863, -0.0879);

    float a_corr = (temp_corr_a + 538.2376 + 499.0689) / 3.0;
    float b_corr = (temp_corr_b + -0.0733 + -0.0722) / 3.0;

    float curve = time_curve(x);
    return 3500.0 / inverseYaxb(a_corr, curve, b_corr);
}

float MG811::calculateppm(float SensorValue, float temp, float rh, float correction, int idx) {
    GasData g = gases[idx];
    float emf = fmap(SensorValue, 0, 1, g.emf_max, g.emf_min);
    float a_gas, b_gas;
    
    switch (idx) {
        case 0: // CH4
            a_gas = 326.7924; b_gas = -0.0017;
            break;
    
        case 1: // C2H5OH
            if (emf > 322.2195) { a_gas = 327.3446; b_gas = -0.0024; }
            else if (emf <= 322.2195 && emf > 321.0224) { a_gas = 350.0226; b_gas = -0.0129; }
            else if (emf <= 321.0224) { a_gas = 333.2081; b_gas = -0.0056; }
            break;
    
        case 2: // CO
            if (emf > 320.0249) { a_gas = 332.606; b_gas = -0.0061; }
            else if (emf <= 320.0249 && emf > 315.4364) { a_gas = 383.6791; b_gas = -0.0284; }
            else if (emf <= 315.4364 && emf > 298.0798) { a_gas = 827.293; b_gas = -0.1396; }
            else if (emf <= 298.0798 && emf > 280.5237) { a_gas = 468.501; b_gas = -0.0618; }
            else if (emf <= 280.5237) { a_gas = 483.2887; b_gas = -0.0654; }
            break;
    
        case 3: // CO2
            a_gas = 499.0689; b_gas = -0.0722;
            break;
    }
    
    float a_temp, b_temp;
    
    if (temp <= -10) {
        a_temp = 522.7202; b_temp = -0.0843;
    } else if (temp <= 0) {
        a_temp = fmap(temp, -10, 0, 522.7202, 517.0238);
        b_temp = fmap(temp, -10, 0, -0.0843, -0.0833);
    } else if (temp <= 10) {
        a_temp = fmap(temp, 0, 10, 517.0238, 520.9298);
        b_temp = fmap(temp, 0, 10, -0.0833, -0.0849);
    } else if (temp <= 20) {
        a_temp = fmap(temp, 10, 20, 520.9298, 523.094);
        b_temp = fmap(temp, 10, 20, -0.0849, -0.0863);
    } else if (temp <= 30) {
        a_temp = fmap(temp, 20, 30, 523.094, 527.0596);
        b_temp = fmap(temp, 20, 30, -0.0863, -0.0879);
    } else if (temp < 50) {
        a_temp = fmap(temp, 30, 50, 527.0596, 527.0802);
        b_temp = fmap(temp, 30, 50, -0.0879, -0.0891);
    } else if (temp >= 50) {
        a_temp = 527.0802; 
        b_temp = -0.0891;
    }
    
    float a_rh, b_rh;
    
    if (rh <= 40) {
        a_rh = 536.8846; b_rh = -0.0726;
    } else if (rh <= 65) {
        a_rh = fmap(rh, 40, 65, 536.8846, 538.2376);
        b_rh = fmap(rh, 40, 65, -0.0726, -0.0733);
    } else if (rh < 85) {
        a_rh = fmap(rh, 65, 85, 538.2376, 529.1227);
        b_rh = fmap(rh, 65, 85, -0.0733, -0.0717);
    } else if (rh >= 85) {
        a_rh = 529.1227; 
        b_rh = -0.0717;
    }

    float a_avg = (a_temp + a_rh + a_gas) / 3;
    float b_avg = (b_temp + b_rh + b_gas) / 3;

    return inverseYaxb(a_avg, emf, b_avg) * correction;
}

float MG811::TheoreticalCO2(float x) {
  float polynomial = 5.0000 * pow(x, 1) + 6.5833 * pow(x, 2) - 4.9167 * pow(x, 3); // RMSE: 0.8484
  return 1000.0 - 600.0 * exp(-polynomial);
}
