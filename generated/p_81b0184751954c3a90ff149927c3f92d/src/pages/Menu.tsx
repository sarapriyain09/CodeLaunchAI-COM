export default function Menu() {
  return (
    <div className="flex flex-col items-center bg-gray-100">
      <header className="w-full bg-white shadow">
        <h1 className="text-3xl font-bold text-center py-6">Menu</h1>
      </header>
      <section className="w-full max-w-4xl p-6">
        <img
          src="https://picsum.photos/seed/hero-menu/1200/400"
          alt="Delicious food spread"
          className="w-full rounded-lg mb-6"
        />
        <h2 className="text-2xl font-semibold mb-4">Our Specialties</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          <div className="bg-white rounded-lg shadow p-4">
            <img
              src="https://picsum.photos/seed/card-menu-1/400/300"
              alt="Gourmet dish 1"
              className="w-full rounded-lg mb-2"
            />
            <h3 className="font-bold">Gourmet Dish 1</h3>
            <p className="text-gray-600">A delightful blend of flavors.</p>
          </div>
          <div className="bg-white rounded-lg shadow p-4">
            <img
              src="https://picsum.photos/seed/card-menu-2/400/300"
              alt="Gourmet dish 2"
              className="w-full rounded-lg mb-2"
            />
            <h3 className="font-bold">Gourmet Dish 2</h3>
            <p className="text-gray-600">A taste of elegance and tradition.</p>
          </div>
          <div className="bg-white rounded-lg shadow p-4">
            <img
              src="https://picsum.photos/seed/card-menu-3/400/300"
              alt="Gourmet dish 3"
              className="w-full rounded-lg mb-2"
            />
            <h3 className="font-bold">Gourmet Dish 3</h3>
            <p className="text-gray-600">A perfect choice for any occasion.</p>
          </div>
        </div>
      </section>
      <section className="w-full max-w-4xl p-6 bg-white rounded-lg shadow mt-6">
        <h2 className="text-2xl font-semibold mb-4">Contact Us</h2>
        <p className="mb-4">For inquiries, reach out via WhatsApp:</p>
        <a
          href="https://wa.me/1234567890"
          className="inline-block bg-green-500 text-white py-2 px-4 rounded hover:bg-green-600 transition"
        >
          Message Us on WhatsApp
        </a>
      </section>
    </div>
  );
}
