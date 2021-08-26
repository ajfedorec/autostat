from ..constraints import KernelConstraints, default_constraints
import typing as ty


from sklearn.gaussian_process.kernels import (
    RBF,
    ConstantKernel,
    DotProduct,
    Kernel,
    Product,
    RationalQuadratic,
    Sum,
    WhiteKernel,
    ExpSineSquared,
)

from .custom_periodic_kernel import PeriodicKernelNoConstant

from ..kernel_specs import (
    AdditiveKernelSpec,
    KernelSpec,
    LinearKernelSpec,
    PeriodicKernelSpec,
    PeriodicNoConstKernelSpec,
    ProductKernelSpec,
    RBFKernelSpec,
    RQKernelSpec,
    TopLevelKernelSpec,
)


def build_kernel_additive(
    kernel_spec: AdditiveKernelSpec, constraints: KernelConstraints
) -> ty.Union[Sum, Product]:

    inner = build_kernel(kernel_spec.operands[0], constraints)
    if len(kernel_spec.operands) == 1:
        return ty.cast(Product, inner)

    for product in kernel_spec.operands[1:-1]:
        inner += build_kernel(product, constraints)
    inner += build_kernel(kernel_spec.operands[-1], constraints)
    return inner


def build_kernel(kernel_spec: KernelSpec, constraints: KernelConstraints) -> Kernel:

    constraints = constraints or default_constraints()

    if isinstance(kernel_spec, RBFKernelSpec):
        inner = RBF(length_scale=kernel_spec.length_scale)

    elif isinstance(kernel_spec, LinearKernelSpec):
        inner = DotProduct(sigma_0=kernel_spec.variance)

    elif isinstance(kernel_spec, PeriodicNoConstKernelSpec):
        kwargs = {
            "periodicity_bounds": constraints.PER.period,
            "length_scale_bounds": constraints.PER.length_scale,
        }
        inner = PeriodicKernelNoConstant(
            length_scale=kernel_spec.length_scale,
            periodicity=kernel_spec.period,
            **kwargs
        )

    elif isinstance(kernel_spec, PeriodicKernelSpec):
        kwargs = {
            "periodicity_bounds": constraints.PER.period,
            "length_scale_bounds": constraints.PER.length_scale,
        }
        inner = ExpSineSquared(
            length_scale=kernel_spec.length_scale,
            periodicity=kernel_spec.period,
            **kwargs
        )

    elif isinstance(kernel_spec, RQKernelSpec):
        inner = RationalQuadratic(
            length_scale=kernel_spec.length_scale, alpha=kernel_spec.alpha
        )

    elif isinstance(kernel_spec, AdditiveKernelSpec):
        inner = build_kernel_additive(kernel_spec, constraints)

    elif isinstance(kernel_spec, ProductKernelSpec):
        inner = ConstantKernel(constant_value=kernel_spec.scalar)
        for operand in kernel_spec.operands:
            inner *= build_kernel(operand, constraints)

    else:
        print("invalid kernel_spec type -- type(kernel_spec):", type(kernel_spec))
        print(kernel_spec)
        raise TypeError("Invalid kernel spec type")

    if isinstance(kernel_spec, TopLevelKernelSpec):
        inner = build_kernel_additive(kernel_spec, constraints)
        inner = inner + WhiteKernel(noise_level=kernel_spec.noise)

    return inner