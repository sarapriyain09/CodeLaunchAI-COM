export default function Products() {
  return (
    <div className="bg-white">
      <header className="relative">
        <img
          src="https://picsum.photos/seed/hero-products/1200/700"
          alt="Elegant jewellery display"
          className="w-full h-64 object-cover"
        />
        <h1 className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 text-white text-4xl font-bold">
          Explore Our Collection
        </h1>
      </header>
      <section className="py-10 px-4">
        <h2 className="text-2xl font-semibold text-center mb-6">Featured Products</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-6">
          <div className="border rounded-lg overflow-hidden shadow-lg">
            <img
              src="https://picsum.photos/seed/card-products-1/400/300"
              alt="Minimalist gold ring"
              className="w-full h-48 object-cover"
            />
            <div className="p-4">
              <h3 className="text-lg font-medium">Gold Ring</h3>
              <p className="text-gray-600">$150.00</p>
            </div>
          </div>
          <div className="border rounded-lg overflow-hidden shadow-lg">
            <img
              src="https://picsum.photos/seed/card-products-2/400/300"
              alt="Elegant silver necklace"
              className="w-full h-48 object-cover"
            />
            <div className="p-4">
              <h3 className="text-lg font-medium">Silver Necklace</h3>
              <p className="text-gray-600">$120.00</p>
            </div>
          </div>
          <div className="border rounded-lg overflow-hidden shadow-lg">
            <img
              src="https://picsum.photos/seed/card-products-3/400/300"
              alt="Stylish bracelet"
              className="w-full h-48 object-cover"
            />
            <div className="p-4">
              <h3 className="text-lg font-medium">Stylish Bracelet</h3>
              <p className="text-gray-600">$90.00</p>
            </div>
          </div>
        </div>
      </section>
      <section className="bg-gray-100 py-10 px-4">
        <h2 className="text-2xl font-semibold text-center mb-6">Join Our Newsletter</h2>
        <p className="text-center mb-4">Stay updated with our latest collections and offers.</p>
        <form className="flex justify-center">
          <input
            type="email"
            placeholder="Enter your email"
            className="border rounded-l-lg p-2 w-1/3"
            required
          />
          <button className="bg-blue-500 text-white rounded-r-lg p-2">Subscribe</button>
        </form>
      </section>
    </div>
  );
}
