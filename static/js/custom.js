let autocomplete;
let navbarAutocomplete;

// Make sure initAutoComplete is globally accessible
function initAutoComplete() {
  // Initialize autocomplete for search form (home page)
  const addressInput = document.getElementById("id_address");
  if (addressInput) {
    initSearchFormAutocomplete(addressInput);
  }
  
  // Initialize autocomplete for navbar location
  const locationInput = document.getElementById("location");
  if (locationInput) {
    initNavbarAutocomplete(locationInput);
  }
}

// Initialize autocomplete for search form
function initSearchFormAutocomplete(addressInput) {
  // Get user's current location first
  if (navigator.geolocation) {
    navigator.geolocation.getCurrentPosition(
      function(position) {
        const userLocation = {
          lat: position.coords.latitude,
          lng: position.coords.longitude
        };
        
        // Create bounds around user's location (roughly 20km radius)
        const bounds = new google.maps.LatLngBounds(
          new google.maps.LatLng(userLocation.lat - 0.1, userLocation.lng - 0.1),
          new google.maps.LatLng(userLocation.lat + 0.1, userLocation.lng + 0.1)
        );
        
        // Initialize autocomplete with location bias
        autocomplete = new google.maps.places.Autocomplete(
          addressInput,
          {
            types: ["geocode", "establishment"],
            componentRestrictions: { country: ["in"] },
            bounds: bounds,
            strictBounds: false,
            fields: ["address_components", "geometry", "name"]
          }
        );
        
        // Ensure proper CSS for dropdown
        setupAutoCompleteCSS();
        
        autocomplete.addListener("place_changed", onPlaceChanged);
      },
      function(error) {
        console.log("Geolocation failed:", error);
        // Fallback: Initialize without location bias
        initSearchAutocompleteWithoutLocation(addressInput);
      }
    );
  } else {
    console.log("Geolocation not supported");
    initSearchAutocompleteWithoutLocation(addressInput);
  }
}

// Initialize autocomplete for navbar location input
function initNavbarAutocomplete(locationInput) {
  // Get user's current location first
  if (navigator.geolocation) {
    navigator.geolocation.getCurrentPosition(
      function(position) {
        const userLocation = {
          lat: position.coords.latitude,
          lng: position.coords.longitude
        };
        
        // Create bounds around user's location
        const bounds = new google.maps.LatLngBounds(
          new google.maps.LatLng(userLocation.lat - 0.1, userLocation.lng - 0.1),
          new google.maps.LatLng(userLocation.lat + 0.1, userLocation.lng + 0.1)
        );
        
        // Initialize navbar autocomplete
        navbarAutocomplete = new google.maps.places.Autocomplete(
          locationInput,
          {
            types: ["geocode", "establishment"],
            componentRestrictions: { country: ["in"] },
            bounds: bounds,
            strictBounds: false,
            fields: ["address_components", "geometry", "name"]
          }
        );
        
        // Ensure proper CSS for dropdown
        setupAutoCompleteCSS();
        
        navbarAutocomplete.addListener("place_changed", onNavbarPlaceChanged);
      },
      function(error) {
        console.log("Navbar geolocation failed:", error);
        // Fallback: Initialize without location bias
        initNavbarAutocompleteWithoutLocation(locationInput);
      }
    );
  } else {
    console.log("Geolocation not supported for navbar");
    initNavbarAutocompleteWithoutLocation(locationInput);
  }
}

// Fallback function for search form when geolocation fails
function initSearchAutocompleteWithoutLocation(addressInput) {
  autocomplete = new google.maps.places.Autocomplete(
    addressInput,
    {
      types: ["geocode", "establishment"],
      componentRestrictions: { country: ["in"] },
      fields: ["address_components", "geometry", "name"]
    }
  );
  
  setupAutoCompleteCSS();
  autocomplete.addListener("place_changed", onPlaceChanged);
}

// Fallback function for navbar when geolocation fails
function initNavbarAutocompleteWithoutLocation(locationInput) {
  navbarAutocomplete = new google.maps.places.Autocomplete(
    locationInput,
    {
      types: ["geocode", "establishment"],
      componentRestrictions: { country: ["in"] },
      fields: ["address_components", "geometry", "name"]
    }
  );
  
  setupAutoCompleteCSS();
  navbarAutocomplete.addListener("place_changed", onNavbarPlaceChanged);
}

// Function to ensure proper CSS for autocomplete dropdown
function setupAutoCompleteCSS() {
  // Check if style already exists to avoid duplicates
  if (document.getElementById('pac-style')) {
    return;
  }
  
  // Add CSS to ensure dropdown is visible and clickable
  const style = document.createElement('style');
  style.id = 'pac-style';
  style.textContent = `
    .pac-container {
      z-index: 10000 !important;
      position: absolute !important;
      background-color: white !important;
      border: 1px solid #ccc !important;
      border-radius: 4px !important;
      box-shadow: 0 2px 6px rgba(0,0,0,0.3) !important;
      max-width: 90% !important;
    }
    .pac-item {
      cursor: pointer !important;
      padding: 8px 12px !important;
      text-overflow: ellipsis !important;
      white-space: nowrap !important;
      overflow: hidden !important;
      background-color: white !important;
      border-bottom: 1px solid #e6e6e6 !important;
      line-height: 1.4 !important;
    }
    .pac-item:hover,
    .pac-item-selected {
      background-color: #fafafa !important;
    }
    .pac-item-query {
      font-size: 13px !important;
      color: #333 !important;
    }
    .pac-matched {
      font-weight: bold !important;
      color: #000 !important;
    }
    .pac-item:last-child {
      border-bottom: none !important;
    }
    /* Ensure input field styling doesn't interfere */
    #location {
      position: relative !important;
      z-index: 1 !important;
    }
    #id_address {
      position: relative !important;
      z-index: 1 !important;
    }
  `;
  document.head.appendChild(style);
}

// Handler for navbar location selection
function onNavbarPlaceChanged() {
  var place = navbarAutocomplete.getPlace();

  if (!place.geometry) {
    document.getElementById("location").placeholder = "Start typing...";
    return;
  }

  console.log("Navbar place selected:", place.name);
  
  // Update navbar location display
  var selectedLocation = place.name || place.formatted_address;
  document.getElementById("location").value = selectedLocation;
  
  // Extract location components and store them
  var locationComponents = {
    lat: place.geometry.location.lat(),
    lng: place.geometry.location.lng(),
    sublocality: '',
    locality: '',
    district: '',
    state: '',
    country: ''
  };
  
  // Parse address components
  for (var i = 0; i < place.address_components.length; i++) {
    var component = place.address_components[i];
    var types = component.types;
    
    if (types.includes('sublocality_level_1') || types.includes('sublocality')) {
      locationComponents.sublocality = component.long_name;
    } else if (types.includes('locality')) {
      locationComponents.locality = component.long_name;
    } else if (types.includes('administrative_area_level_3')) {
      locationComponents.district = component.long_name;
    } else if (types.includes('administrative_area_level_1')) {
      locationComponents.state = component.long_name;
    } else if (types.includes('country')) {
      locationComponents.country = component.long_name;
    }
  }
  
  // Store in session storage
  sessionStorage.setItem('current_lat', locationComponents.lat);
  sessionStorage.setItem('current_lng', locationComponents.lng);
  sessionStorage.setItem('current_sublocality', locationComponents.sublocality);
  sessionStorage.setItem('current_city', locationComponents.locality);
  sessionStorage.setItem('current_state', locationComponents.state);
  
  console.log("Navbar location components stored:", locationComponents);
}

function onPlaceChanged() {
  var place = autocomplete.getPlace();

  // User did not select the prediction. Reset the input field or alert()
  if (!place.geometry) {
    document.getElementById("id_address").placeholder = "Start typing...";
  } else {
    console.log("place name=>", place.name);
  }

  // get the address components and assign them to the fields
  console.log(place);
  var geocoder = new google.maps.Geocoder();
  var address = document.getElementById("id_address").value;

  geocoder.geocode({ address: address }, function (results, status) {
    console.log("results=>", results);
    console.log("status=>", status);
    if (status == google.maps.GeocoderStatus.OK) {
      var latitude = results[0].geometry.location.lat();
      var longitude = results[0].geometry.location.lng();

      console.log("lat=>", latitude);
      console.log("long=>", longitude);
      $("#id_latitude").val(latitude);
      $("#id_longitude").val(longitude);

      $("#id_address").val(address);
    }
  });

  // loop through the address components and assign other address data
  console.log(place.address_components);
  for (var i = 0; i < place.address_components.length; i++) {
    for (var j = 0; j < place.address_components[i].types.length; j++) {
      // get country
      if (place.address_components[i].types[j] == "country") {
        $("#id_country").val(place.address_components[i].long_name);
      }
      // get state
      if (
        place.address_components[i].types[j] == "administrative_area_level_1"
      ) {
        $("#id_state").val(place.address_components[i].long_name);
      }
      // get city
      if (place.address_components[i].types[j] == "locality") {
        $("#id_city").val(place.address_components[i].long_name);
      }
      // get pincode
      if (place.address_components[i].types[j] == "postal_code") {
        $("#id_pin_code").val(place.address_components[i].long_name);
      } else {
        $("#id_pin_code").val("");
      }
    }
  }
}

$(document).ready(function () {
  // add to cart
  $(".add_to_cart").on("click", function (e) {
    e.preventDefault();

    food_id = $(this).attr("data-id");
    url = $(this).attr("data-url");

    $.ajax({
      type: "GET",
      url: url,
      success: function (response) {
        console.log(response);
        if (response.status == "login_required") {
          swal(response.message, "", "info").then(function () {
            window.location = "/login";
          });
        } else if (response.status == "Failed") {
          swal(response.message, "", "error");
        } else {
          $("#cart_counter").html(response.cart_counter["cart_count"]);
          $("#qty-" + food_id).html(response.qty);

          // subtotal, tax and grand total
          applyCartAmounts(
            response.cart_amount["subtotal"],
            response.cart_amount["tax_dict"],
            response.cart_amount["grand_total"]
          );
        }
      },
    });
  });

  // place the cart item quantity on load
  $(".item_qty").each(function () {
    var the_id = $(this).attr("id");
    var qty = $(this).attr("data-qty");
    $("#" + the_id).html(qty);
  });

  // decrease cart
  $(".decrease_cart").on("click", function (e) {
    e.preventDefault();

    food_id = $(this).attr("data-id");
    url = $(this).attr("data-url");
    cart_id = $(this).attr("id");

    $.ajax({
      type: "GET",
      url: url,
      success: function (response) {
        console.log(response);
        if (response.status == "login_required") {
          swal(response.message, "", "info").then(function () {
            window.location = "/login";
          });
        } else if (response.status == "Failed") {
          swal(response.message, "", "error");
        } else {
          $("#cart_counter").html(response.cart_counter["cart_count"]);
          $("#qty-" + food_id).html(response.qty);

          applyCartAmounts(
            response.cart_amount["subtotal"],
            response.cart_amount["tax_dict"],
            response.cart_amount["grand_total"]
          );

          if (window.location.pathname == "/cart/") {
            removeCartItem(response.qty, cart_id);
            checkEmptyCart();
          }
        }
      },
    });
  });

  // DELETE CART ITEM
  $(".delete_cart").on("click", function (e) {
    e.preventDefault();

    cart_id = $(this).attr("data-id");
    url = $(this).attr("data-url");

    $.ajax({
      type: "GET",
      url: url,
      success: function (response) {
        console.log(response);
        if (response.status == "Failed") {
          swal(response.message, "", "error");
        } else {
          $("#cart_counter").html(response.cart_counter["cart_count"]);
          swal(response.status, response.message, "success");

          applyCartAmounts(
            response.cart_amount["subtotal"],
            response.cart_amount["tax_dict"],
            response.cart_amount["grand_total"]
          );

          removeCartItem(0, cart_id);
          checkEmptyCart();
        }
      },
    });
  });

  // delete the cart element if the qty is 0
  function removeCartItem(cartItemQty, cart_id) {
    if (cartItemQty <= 0) {
      // remove the cart item element
      document.getElementById("cart-item-" + cart_id).remove();
    }
  }

  // Check if the cart is empty
  function checkEmptyCart() {
    var cart_counter = document.getElementById("cart_counter").innerHTML;
    if (cart_counter == 0) {
      document.getElementById("empty-cart").style.display = "block";
    }
  }

  // apply cart amounts
  function applyCartAmounts(subtotal, tax_dict, grand_total) {
    if (window.location.pathname == "/cart/") {
      $("#subtotal").html(subtotal);
      $("#total").html(grand_total);

      console.log(tax_dict);
      for (key1 in tax_dict) {
        console.log(tax_dict[key1]);
        for (key2 in tax_dict[key1]) {
          // console.log(tax_dict[key1][key2])
          $("#tax-" + key1).html(tax_dict[key1][key2]);
        }
      }
    }
  }

  // ADD OPENING HOUR
  $(".add_hour").on("click", function (e) {
    e.preventDefault();
    var day = document.getElementById("id_day").value;
    var from_hour = document.getElementById("id_from_hour").value;
    var to_hour = document.getElementById("id_to_hour").value;
    var is_closed = document.getElementById("id_is_closed").checked;
    var csrf_token = $("input[name=csrfmiddlewaretoken]").val();
    var url = document.getElementById("add_hour_url").value;

    console.log(day, from_hour, to_hour, is_closed, csrf_token);

    if (is_closed) {
      is_closed = "True";
      condition = "day != ''";
    } else {
      is_closed = "False";
      condition = "day != '' && from_hour != '' && to_hour != ''";
    }

    if (eval(condition)) {
      $.ajax({
        type: "POST",
        url: url,
        data: {
          day: day,
          from_hour: from_hour,
          to_hour: to_hour,
          is_closed: is_closed,
          csrfmiddlewaretoken: csrf_token,
        },
        success: function (response) {
          if (response.status == "success") {
            if (response.is_closed == "Closed") {
              html =
                '<tr id="hour-' +
                response.id +
                '"><td><b>' +
                response.day +
                '</b></td><td>Closed</td><td><a href="#" class="remove_hour" data-url="/vendor/opening-hours/remove/' +
                response.id +
                '/">Remove</a></td></tr>';
            } else {
              html =
                '<tr id="hour-' +
                response.id +
                '"><td><b>' +
                response.day +
                "</b></td><td>" +
                response.from_hour +
                " - " +
                response.to_hour +
                '</td><td><a href="#" class="remove_hour" data-url="/vendor/opening-hours/remove/' +
                response.id +
                '/">Remove</a></td></tr>';
            }

            $(".opening_hours").append(html);
            document.getElementById("opening_hours").reset();
          } else {
            swal(response.message, "", "error");
          }
        },
      });
    } else {
      swal("Please fill all fields", "", "info");
    }
  });

  // REMOVE OPENING HOUR
  $(document).on("click", ".remove_hour", function (e) {
    e.preventDefault();
    url = $(this).attr("data-url");

    $.ajax({
      type: "GET",
      url: url,
      success: function (response) {
        if (response.status == "success") {
          document.getElementById("hour-" + response.id).remove();
        }
      },
    });
  });
  // document ready close
});

// Ensure initAutoComplete is globally accessible for Google Maps callback
window.initAutoComplete = initAutoComplete;
