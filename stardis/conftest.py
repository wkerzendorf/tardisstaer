import pytest
from pathlib import Path
import numpy as np
from astropy import units as u

from tardis.io.atom_data.base import AtomData
from tardis.io.atom_data.util import download_atom_data
from tardis.io.configuration.config_validator import validate_yaml
from tardis.io.configuration.config_reader import Configuration
from stardis.io.model.marcs import read_marcs_model
from stardis.plasma import create_stellar_plasma
from stardis.radiation_field.opacities.opacities_solvers import calc_alphas
from stardis.radiation_field.radiation_field_solvers import raytrace
from stardis.radiation_field import RadiationField
from stardis.radiation_field.source_functions.blackbody import blackbody_flux_at_nu
from stardis import STARDISOutput
from stardis.io.base import SCHEMA_PATH

EXAMPLE_CONF_PATH = Path(__file__).parent / "tests" / "stardis_test_config.yml"
EXAMPLE_CONF_PATH_BROADENING = (
    Path(__file__).parent / "tests" / "stardis_test_config_broadening.yml"
)
EXAMPLE_CONF_PATH_PARALLEL = (
    Path(__file__).parent / "tests" / "stardis_test_config_parallel.yml"
)


@pytest.fixture(scope="session")
def example_tracing_nus():
    return (np.arange(6560, 6570, 0.1) * u.Angstrom).to(
        u.Hz, equivalencies=u.spectral()
    )


@pytest.fixture(scope="session")
def example_kurucz_atomic_data():
    download_atom_data("kurucz_cd23_chianti_H_He")
    return AtomData.from_hdf("kurucz_cd23_chianti_H_He.h5")


@pytest.fixture(scope="session")
def example_config():
    config_dict = validate_yaml(EXAMPLE_CONF_PATH, schemapath=SCHEMA_PATH)
    return Configuration(config_dict)


@pytest.fixture(scope="session")
def example_config_broadening():
    config_dict = validate_yaml(EXAMPLE_CONF_PATH_BROADENING, schemapath=SCHEMA_PATH)
    return Configuration(config_dict)


@pytest.fixture(scope="session")
def example_config_parallel():
    config_dict = validate_yaml(EXAMPLE_CONF_PATH_PARALLEL, schemapath=SCHEMA_PATH)
    return Configuration(config_dict)


@pytest.fixture(scope="session")
def example_stellar_model(example_config, example_kurucz_atomic_data):
    raw_marcs_model = read_marcs_model(
        Path(example_config.model.fname), gzipped=example_config.model.gzipped
    )
    return raw_marcs_model.to_stellar_model(
        example_kurucz_atomic_data,
        final_atomic_number=example_config.model.final_atomic_number,
    )


@pytest.fixture(scope="session")
def example_stellar_plasma(
    example_stellar_model, example_kurucz_atomic_data, example_config
):
    example_kurucz_atomic_data.prepare_atom_data(
        np.arange(
            1,
            np.min(
                [
                    len(example_stellar_model.composition.element_masses),
                    example_config.model.final_atomic_number,
                ]
            )
            + 1,
        ),
        line_interaction_type="macroatom",
        nlte_species=[],
        continuum_interaction_species=[],
    )
    return create_stellar_plasma(
        example_stellar_model, example_kurucz_atomic_data, example_config
    )


@pytest.fixture(scope="session")
def example_stellar_radiation_field(
    example_stellar_model, example_config, example_tracing_nus, example_stellar_plasma
):
    stellar_radiation_field = RadiationField(
        example_tracing_nus, blackbody_flux_at_nu, example_stellar_model
    )

    calc_alphas(
        stellar_plasma=example_stellar_plasma,
        stellar_model=example_stellar_model,
        stellar_radiation_field=stellar_radiation_field,
        opacity_config=example_config.opacity,
    )

    raytrace(
        example_stellar_model,
        stellar_radiation_field,
        no_of_thetas=example_config.no_of_thetas,
    )
    return stellar_radiation_field


@pytest.fixture(scope="session")
def example_stellar_radiation_field_broadening(
    example_stellar_model,
    example_config_broadening,
    example_tracing_nus,
    example_stellar_plasma,
):
    stellar_radiation_field = RadiationField(
        example_tracing_nus, blackbody_flux_at_nu, example_stellar_model
    )

    calc_alphas(
        stellar_plasma=example_stellar_plasma,
        stellar_model=example_stellar_model,
        stellar_radiation_field=stellar_radiation_field,
        opacity_config=example_config_broadening.opacity,
    )

    raytrace(
        example_stellar_model,
        stellar_radiation_field,
        no_of_thetas=example_config_broadening.no_of_thetas,
    )
    return stellar_radiation_field


@pytest.fixture(scope="session")
def example_stellar_radiation_field_parallel(
    example_stellar_model,
    example_config_parallel,
    example_tracing_nus,
    example_stellar_plasma,
):
    stellar_radiation_field = RadiationField(
        example_tracing_nus, blackbody_flux_at_nu, example_stellar_model
    )

    calc_alphas(
        stellar_plasma=example_stellar_plasma,
        stellar_model=example_stellar_model,
        stellar_radiation_field=stellar_radiation_field,
        opacity_config=example_config_parallel.opacity,
        n_threads=example_config_parallel.n_threads,
    )

    raytrace(
        example_stellar_model,
        stellar_radiation_field,
        no_of_thetas=example_config_parallel.no_of_thetas,
        n_threads=example_config_parallel.n_threads,
    )
    return stellar_radiation_field


@pytest.fixture(scope="session")
def example_stardis_output(
    example_stellar_model,
    example_stellar_plasma,
    example_stellar_radiation_field,
    example_config,
):
    return STARDISOutput(
        example_config.result_options,
        example_stellar_model,
        example_stellar_plasma,
        example_stellar_radiation_field,
    )


@pytest.fixture(scope="session")
def example_stardis_output_broadening(
    example_stellar_model,
    example_stellar_plasma,
    example_stellar_radiation_field_broadening,
    example_config_broadening,
):
    return STARDISOutput(
        example_config_broadening.result_options,
        example_stellar_model,
        example_stellar_plasma,
        example_stellar_radiation_field_broadening,
    )


@pytest.fixture(scope="session")
def example_stardis_output_parallel(
    example_stellar_model,
    example_stellar_plasma,
    example_stellar_radiation_field_parallel,
    example_config_parallel,
):
    return STARDISOutput(
        example_config_parallel.result_options,
        example_stellar_model,
        example_stellar_plasma,
        example_stellar_radiation_field_parallel,
    )
