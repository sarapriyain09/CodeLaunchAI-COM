export default function ProductsId() {
  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      <section className="mb-8">
        <img
          src="https://picsum.photos/seed/hero-products-1/1200/700"
          alt="Elegant jewelry display"
          className="w-full h-auto rounded-lg shadow-lg"
        />
      </section>
      <section className="mb-8">
        <h1 className="text-3xl font-bold mb-4">Elegant Gold Necklace</h1>
        <p className="text-lg text-gray-700 mb-4">
          This stunning gold necklace is perfect for any occasion, adding a touch of elegance to your outfit.
        </p>
        <span className="text-xl font-semibold text-gray-900">$199.99</span>
      </section>
      <section className="mb-8">
        <h2 className="text-2xl font-semibold mb-4">Product Gallery</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
          <img
            src="https://picsum.photos/seed/card-products-1-1/400/300"
            alt="Close-up of gold necklace"
            className="w-full h-auto rounded-lg shadow-md"
          />
          <img
            src="https://picsum.photos/seed/card-products-1-2/400/300"
            alt="Gold necklace on a model"
            className="w-full h-auto rounded-lg shadow-md"
          />
          <img
            src="https://picsum.photos/seed/card-products-1-3/400/300"
            alt="Gold necklace with earrings"
            className="w-full h-auto rounded-lg shadow-md"
          />
        </div>
      </section>
      <section className="text-center">
        <h2 className="text-2xl font-semibold mb-4">Ready to Shine?</h2>
        <p className="text-lg text-gray-700 mb-4">
          Elevate your style with our exquisite jewelry collection. Don’t miss out!
        </p>
        <button className="bg-blue-600 text-white py-2 px-4 rounded-lg hover:bg-blue-700 transition duration-300">
          Add to Cart
        </button>
      </section>
    </div>
  );
}
