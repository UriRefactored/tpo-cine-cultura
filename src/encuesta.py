"""Estimación con diseño muestral complejo (linealización de Taylor, "conglomerado último").

Diseño ENCC 2022/23 (docs/fuentes/encc_2022_23_diseno_muestral.pdf): estratificación por región; primera
etapa = localidades; luego radios censales, hogares y una persona por hogar (con cuotas de sexo y edad).

Aproximación usada (documentada en el README):
- Estrato = región; UPM = localidad. La varianza se estima con los totales por UPM centrados dentro de cada
  estrato, con factor n_h/(n_h-1). Es el estimador estándar de "conglomerado último" (como svyglm en R).
- CABA tiene una única localidad (UPM de inclusión forzosa). Dentro de ese estrato se usan las personas como
  unidades de varianza; al no disponer de los radios censales, esto probablemente subestima algo la varianza
  de CABA.
- Grados de libertad para las pruebas t: (#UPM − #estratos).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
import patsy
from scipy import stats


@dataclass
class Diseno:
    peso: np.ndarray
    estrato: np.ndarray
    upm: np.ndarray
    gl: int

    @classmethod
    def desde(cls, df: pd.DataFrame, peso="ponderador", estrato="region", upm="localidad") -> "Diseno":
        e = df[estrato].astype(str).to_numpy()
        u = df[upm].astype(str).to_numpy()
        # Estratos con una sola UPM: las personas pasan a ser las unidades de varianza
        n_upm = pd.Series(u).groupby(e).transform("nunique").to_numpy()
        u = np.where(n_upm == 1, np.char.add(np.char.add(e.astype(str), "_persona_"), np.arange(len(df)).astype(str)), u)
        n_upm_total = len(set(df[upm].astype(str)))
        gl = n_upm_total - len(set(e))
        return cls(df[peso].to_numpy(float), e, u, gl)

    def var_total(self, z: np.ndarray) -> np.ndarray:
        """Varianza (matriz si z es 2D) de Σ z_i, con z ya multiplicado por el peso."""
        z = np.atleast_2d(z.T).T if z.ndim == 1 else z
        dfz = pd.DataFrame(z)
        dfz["_e"], dfz["_u"] = self.estrato, self.upm
        tot = dfz.groupby(["_e", "_u"]).sum()
        V = np.zeros((z.shape[1], z.shape[1]))
        for _, g in tot.groupby(level=0):
            n_h = len(g)
            if n_h < 2:
                continue
            d = g.to_numpy() - g.to_numpy().mean(axis=0)
            V += n_h / (n_h - 1) * d.T @ d
        return V

    def t_crit(self, nivel=0.95) -> float:
        return stats.t.ppf(0.5 + nivel / 2, self.gl)


def proporcion(y: pd.Series, dis: Diseno, dominio: np.ndarray | None = None) -> dict:
    """Media ponderada de y (0/1) en un dominio, con IC 95% por linealización. NaN de y fuera del dominio."""
    d = np.ones(len(y), bool) if dominio is None else np.asarray(dominio, bool)
    yv = np.nan_to_num(y.to_numpy(float))
    d = d & ~np.isnan(y.to_numpy(float))
    w = dis.peso * d
    p = (w * yv).sum() / w.sum()
    z = w * (yv - p) / w.sum()
    se = float(np.sqrt(dis.var_total(z)[0, 0]))
    t = dis.t_crit()
    return {"estimacion": p, "ee": se, "ic_inf": max(0.0, p - t * se), "ic_sup": min(1.0, p + t * se), "n": int(d.sum())}


@dataclass
class Logit:
    formula: str
    params: pd.Series
    cov: pd.DataFrame
    gl: int
    n: int
    X: pd.DataFrame
    w: np.ndarray
    dm_info: object

    def tabla(self) -> pd.DataFrame:
        se = np.sqrt(np.diag(self.cov))
        t = stats.t.ppf(0.975, self.gl)
        tval = self.params / se
        return pd.DataFrame({
            "termino": self.params.index, "coef": self.params.values, "ee": se,
            "or": np.exp(self.params.values), "or_ic_inf": np.exp(self.params.values - t * se),
            "or_ic_sup": np.exp(self.params.values + t * se),
            "p_valor": 2 * stats.t.sf(np.abs(tval), self.gl),
        })

    def contraste(self, vector: np.ndarray) -> dict:
        """Combinación lineal de coeficientes (log-odds) con IC y p."""
        est = float(vector @ self.params.values)
        se = float(np.sqrt(vector @ self.cov.values @ vector))
        t = stats.t.ppf(0.975, self.gl)
        return {"or": np.exp(est), "or_ic_inf": np.exp(est - t * se), "or_ic_sup": np.exp(est + t * se),
                "p_valor": float(2 * stats.t.sf(abs(est / se), self.gl))}

    def prob_ajustada(self, df: pd.DataFrame, variable: str, nivel: str) -> tuple[float, np.ndarray]:
        """Estandarización marginal: probabilidad media si toda la población tuviera variable = nivel."""
        cf = df.copy()
        cf[variable] = nivel
        Xc = patsy.build_design_matrices([self.dm_info], cf, return_type="dataframe")[0]
        mu = 1 / (1 + np.exp(-(Xc.values @ self.params.values)))
        w = self.w / self.w.sum()
        p = float((w * mu).sum())
        grad = (w * mu * (1 - mu)) @ Xc.values
        return p, grad

    def diferencia_ajustada(self, df, variable, nivel_a, nivel_b) -> dict:
        pa, ga = self.prob_ajustada(df, variable, nivel_a)
        pb, gb = self.prob_ajustada(df, variable, nivel_b)
        g = ga - gb
        se = float(np.sqrt(g @ self.cov.values @ g))
        t = stats.t.ppf(0.975, self.gl)
        d = pa - pb
        return {"p_a": pa, "p_b": pb, "dif_pp": 100 * d, "dif_ic_inf": 100 * (d - t * se), "dif_ic_sup": 100 * (d + t * se)}


def logit(formula: str, df: pd.DataFrame, diseno: str = "completo", ponderar: bool = True) -> Logit:
    """Regresión logística ponderada (pseudo-máxima verosimilitud) con varianza sándwich según el diseño.

    diseno = "completo" (estratos + UPM), "solo_upm" (cluster-robust por localidad, sin estratos)
    o "iid" (robusta por persona).
    """
    y, X = patsy.dmatrices(formula, df, return_type="dataframe", NA_action="drop")
    sub = df.loc[X.index]
    w = sub["ponderador"].to_numpy(float) if ponderar else np.ones(len(sub))
    w = w / w.mean()
    yv, Xv = y.values.ravel(), X.values

    beta = np.zeros(Xv.shape[1])
    for _ in range(100):  # Newton-Raphson (IRLS), sin regularización
        eta = Xv @ beta
        mu = 1 / (1 + np.exp(-eta))
        grad = Xv.T @ (w * (yv - mu))
        H = (Xv * (w * mu * (1 - mu))[:, None]).T @ Xv
        paso = np.linalg.solve(H, grad)
        beta += paso
        if np.max(np.abs(paso)) < 1e-10:
            break
    else:
        raise RuntimeError(f"No convergió: {formula}")

    mu = 1 / (1 + np.exp(-(Xv @ beta)))
    H = (Xv * (w * mu * (1 - mu))[:, None]).T @ Xv
    Hinv = np.linalg.inv(H)
    scores = Xv * (w * (yv - mu))[:, None]
    if diseno == "completo":
        dis = Diseno.desde(sub)
        B, gl = dis.var_total(scores), dis.gl
    elif diseno == "solo_upm":
        g = pd.DataFrame(scores).groupby(sub["localidad"].to_numpy()).sum().to_numpy()
        G = len(g)
        B, gl = G / (G - 1) * (g - g.mean(0)).T @ (g - g.mean(0)), G - 1
    else:
        n = len(scores)
        B, gl = n / (n - 1) * scores.T @ scores, n - X.shape[1]
    V = Hinv @ B @ Hinv
    cols = X.columns
    return Logit(formula, pd.Series(beta, cols), pd.DataFrame(V, cols, cols), gl, len(sub), X,
                 sub["ponderador"].to_numpy(float) if ponderar else np.ones(len(sub)), X.design_info)
